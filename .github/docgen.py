#!/usr/bin/env python

from configparser import ConfigParser
from datetime import datetime
from json import dumps, loads
from os import listdir
from os.path import isfile
from pathlib import Path
from random import shuffle
from typing import Callable


def get_config(config_path: Path = Path("./.github/config.ini")) -> dict[str, str]:
    parser = ConfigParser()
    parser.read_string(config_path.read_text())
    return dict(parser.defaults())


def categorical_wallpapers(exclude: str | list[str] = []) -> dict[str, list[Path]]:
    exclude = exclude.split(":") if type(exclude) is str else exclude
    return {
        str(category): [Path(picture) for picture in listdir(category) if picture != "README.md"]
        for category in listdir(".")
        if not category.startswith(".") and not isfile(category) and category not in exclude
    }


def create_default_templates():
    """Create default template files if they don't exist"""
    templates_dir = Path(".github/templates")
    templates_dir.mkdir(exist_ok=True)
    
    templates_config_path = Path(".github/templates.json")
    if templates_config_path.exists():
        try:
            default_templates = loads(templates_config_path.read_text(encoding='utf-8'))
        except:
            print("Warning: templates.json is invalid. Please check the JSON format.")
            return
    else:
        print("Warning: templates.json not found. Please create the templates configuration file.")
        return
    
    for template_name, content in default_templates.items():
        template_path = templates_dir / template_name
        if not template_path.exists():
            if isinstance(content, list):
                content = '\n'.join(content)
            template_path.write_text(content, encoding='utf-8')




def get_templates() -> dict[str, str]:
    create_default_templates()
    templates = {}
    for template in listdir(".github/templates"):
        content = Path(f".github/templates/{template}").read_text(encoding='utf-8')
        templates[template] = content
    return templates


def generate_shuffled(
    config: dict[str, str],
    categories: dict[str, list[Path]],
) -> dict[str, list[Path]]:
    results = {}
    choose = int(config["choose"])
    for category, pictures in categories.items():
        shuffle(pictures)
        results[category] = pictures[:choose]
    return results


def prime_templates(
    config: dict[str, str],
    handlers: dict[str, Callable],
    templates: dict[str, str] = get_templates(),
):
    result = {}
    for template, string in templates.items():
        if template in handlers:
            result[template] = handlers[template](template, string, config)
        else:
            try:
                result[template] = string.format(**config)
            except KeyError as e:
                print(f"Warning: Template {template} needs variable {e} that's not in config. Using template as-is.")
                result[template] = string
    return result


def handle_body(_, string: str, config: dict[str, str]) -> str:
    shuffled = generate_shuffled(config, categorical_wallpapers(config["exclude"]))
    results = []
    spacing = "\n" * int(config["spacing"])
    for category, pictures in shuffled.items():
        merged = {"category": category} | config
        results.append(f"## {category}{spacing}")
        for picture in pictures:
            merged["random"] = str(picture)
            merged["random_stem"] = picture.stem
            results.append(string.format(**merged))
        if config["browse"].casefold() == "True".casefold():
            results.append(f"[Browse](../{category}/README.md){spacing}")
    return spacing.join(results)


def handle_category(_, string: str, config: dict[str, str]) -> dict[str, str]:
    results = {}
    spacing = "\n" * int(config["spacing"])
    templates = get_templates()
    header_template = templates.get("category.header.md", "# {category}\n\n")
    
    for category, pictures in categorical_wallpapers().items():
        readme = f"{category}/README.md"
        header_merged = config | {"category": category}
        results[readme] = header_template.format(**header_merged)
        
        for picture in pictures:
            merged = config | {"filepath": str(picture), "filename": picture.stem, "category": category}
            results[readme] = f"{results[readme]}{string.format(**merged)}{spacing}"
    return results


if __name__ == "__main__":
    CONFIG = get_config()
    CONFIG["date"] = datetime.now().strftime("%Y-%m-%d")
    
    primed = prime_templates(CONFIG, {"body.category.md": handle_body, "category.md": handle_category})
    full_templates = ["heading", "body.heading", "body.category", "sources"]
    full_templates = [primed[f"{item}.md"] for item in full_templates]
    partial_template = primed["category.md"]

    if CONFIG["dry"].casefold() == "True".casefold():
        print(dumps({"full": full_templates, "partial": partial_template}))
    else:
        Path("README.md").write_text(("\n" * int(CONFIG["spacing"])).join(full_templates), encoding='utf-8')
        for category, readme in partial_template.items():
            Path(category).write_text(readme, encoding='utf-8')
