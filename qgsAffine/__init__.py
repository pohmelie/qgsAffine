def name():
    return "qgsAffine"


def description():
    return "Apply affine transformations to selected geometries."


def version():
    return "Version 2.0.0"


def icon():
    return "icon.svg"


def qgisMinimumVersion():
    return "3.4"


def classFactory(iface):
    from .module import AffineUI
    return AffineUI(iface)
