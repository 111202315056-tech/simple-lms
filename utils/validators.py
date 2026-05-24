import re


def validate_password(password):
    """Memvalidasi kekuatan password."""
    errors = []

    if len(password) < 8:
        errors.append("Password harus minimal 8 karakter")

    if not re.search(r'[A-Z]', password):
        errors.append("Password harus mengandung huruf besar")

    if not re.search(r'[a-z]', password):
        errors.append("Password harus mengandung huruf kecil")

    if not re.search(r'[0-9]', password):
        errors.append("Password harus mengandung angka")

    if not re.search(r'[!@#$%^&*]', password):
        errors.append("Password harus mengandung karakter spesial (!@#$%^&*)")

    return {
        'is_valid': len(errors) == 0,
        'errors': errors,
    }
