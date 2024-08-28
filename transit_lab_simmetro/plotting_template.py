import plotly.io as pio

template = pio.templates["simple_white"]


def increase_font_size(font_dict, increase_by=8, family="Cambria"):
    if "size" in font_dict and font_dict["size"] is not None:
        font_dict["size"] += increase_by
    else:
        font_dict["size"] = 12 + increase_by  # Assuming default size of 12 if not set
    font_dict["family"] = family  # Set font family to Cambria


# Increase font sizes in various components of the template
increase_font_size(template.layout.title.font)
increase_font_size(template.layout.font)
increase_font_size(template.layout.xaxis.title.font)
increase_font_size(template.layout.yaxis.title.font)
increase_font_size(template.layout.legend.font)

pio.templates.default = template
