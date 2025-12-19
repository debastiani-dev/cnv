import locale


def set_brazilian_locale():
    """
    Force OS formatting to Brazilian Standard
    """
    try:
        locale.setlocale(locale.LC_ALL, "pt_BR.UTF-8")
    except locale.Error:
        print("Warning: pt_BR locale not found. Currency formatting may be incorrect.")
