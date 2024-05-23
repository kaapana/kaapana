import re
from string import Template
from html import escape

from base import ValidationItem

html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>$title</title>
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <meta name="description" content="" />
  <link rel="icon" href="favicon.png">
  <style>
    html {
        font-family: Roboto, sans-serif;
    }
    body {
        margin: 0;
        padding: 15px;
        background-color: #f4f4f4;
        display: block;
    }
    .container{
        max-width: 800px;
        margin: 15px auto;
        background-color: #fff;
        padding: 20px;
        border-radius: 5px;
        display: block;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
    }
    .row{
        display: -webkit-box;
        display: -ms-flexbox;
        display: flex;
        -ms-flex-wrap: wrap;
        flex-wrap: wrap;
        -webkit-box-flex: 1;
        -ms-flex: 1 1 auto;
        flex: 1 1 auto;
        margin: -12px;
    }
    .col{
        width: 100%;
        padding: 12px;
    }
    .col-2{
        -webkit-box-flex: 0;
        -ms-flex: 0 0 15%;
        flex: 0 0 15%;
        max-width: 15%;
    }
    .col-10{
        -webkit-box-flex: 0;
        -ms-flex: 0 0 78%;
        flex: 0 0 78%;
        max-width: 78%;
    }
    h1 {
        font-size: 24px;
        margin-bottom: 20px;
    }
    .attribute {
        font-size: 18px;
        margin-bottom: 8px;
    }
    .error {
        color: red;
        background: rgb(255 119 119 / 50%);
    }
    .warning {
        color: #975300;
        background: rgb(255 190 109 / 50%);
    }
    .validation-item {
    }
    .item-label {
        line-height: 20px;
        max-width: 100%;
        outline: none;
        overflow: hidden;
        padding: 4px 12px;
        position: relative;
        border-radius: 12px;
        text-align: center;
    }
    .item-count-label {
        padding: 2px 8px;
        border-radius: 50%;
        margin-left: 8px;
    }    
    </style>
</head>
<body>
  <div class="container">
    <h1 class="pb-5">$title</h1>
    $attributes
    $errors
    $warnings
  </div>
</body>
</html>
"""


def replace_html_like_tags(target: str):
    tag_templ = re.compile(r"</?(.*)/?>")
    found_tags = re.search(tag_templ, target)
    if found_tags:
        extract = found_tags.group(0)
        text_only = found_tags.group(1)
        target = target.replace(extract, f"<b>{text_only}</b>")
        # print(extract, text_only)
    return target


def get_html_from_validation_item(vitem: ValidationItem, htmlclass: str = "error"):
    validtn_dicoms = ""
    if len(vitem.list_of_dicoms) > 0 and vitem.list_of_dicoms[0] != "all":
        validtn_dicoms = "</br>" + ", ".join(vitem.list_of_dicoms)

    validation_str = f"""
    <div class="row validation-item mt-n3">
    <div class="col col-2"><div class="item-label {htmlclass}">{vitem.tag}</div></div>
    <div class="col col-10"> {vitem.name} {escape(vitem.message)} {validtn_dicoms}</div>
    </div>
    """
    return validation_str


def get_attributes_html_from_dict(attrs: dict):
    attr_html = ""
    for key, val in attrs.items():
        attr_html += f"<div class='attribute mb-2'><strong>{key}:</strong> {val}</div>"

    return attr_html


def generate_html(title: str, attrs: dict, errors: list, warnings: list):
    """
    Generate an HTML string from the given title, attributes, errors, and warnings.

    Args:
        title (str): The title of the HTML document.
        attrs (dict): A dictionary of attributes to be included in the HTML.
        errors (list): A list of ValidationItem objects representing errors.
        warnings (list): A list of ValidationItem objects representing warnings.

    Returns:
        str: The generated HTML as a string.
    """
    html = Template(html_template)

    attrs_str = get_attributes_html_from_dict(attrs)

    err_str = ""
    if len(errors) > 0:
        err_str = f"<h3 class='py-3 mb-3'>Errors <span class='item-count-label error'>{len(errors)}</span></h3>\n"
        for err in errors:
            err_str += get_html_from_validation_item(err, htmlclass="error")

    warn_str = ""
    if len(warnings) > 0:
        warn_str = f"<h3 class='py-3 mb-3'>Warnings <span class='item-count-label warning'>{len(warnings)}</span></h3>\n"
        for warn in warnings:
            warn_str += get_html_from_validation_item(warn, htmlclass="warning")

    return html.substitute(
        title=title, attributes=attrs_str, errors=err_str, warnings=warn_str
    )
