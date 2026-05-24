from django.test import TestCase
from utils.calculator import add, subtract, multiply, divide
from utils.validators import validate_password
from utils.pricing import calculate_discount


class CalculatorTests(TestCase):
    def test_add_positive_numbers(self):
        self.assertEqual(add(2, 3), 5)

    def test_add_negative_numbers(self):
        self.assertEqual(add(-1, -1), -2)

    def test_subtract(self):
        self.assertEqual(subtract(5, 3), 2)

    def test_multiply_by_zero(self):
        self.assertEqual(multiply(5, 0), 0)

    def test_divide_returns_float(self):
        self.assertEqual(divide(7, 2), 3.5)

    def test_divide_by_zero_raises_error(self):
        with self.assertRaises(ValueError):
            divide(10, 0)


class PasswordValidatorTests(TestCase):
    def test_strong_password(self):
        result = validate_password("SecureP@ss1")
        self.assertTrue(result['is_valid'])
        self.assertEqual(result['errors'], [])

    def test_short_password(self):
        result = validate_password("Ab1!")
        self.assertFalse(result['is_valid'])
        self.assertIn("Password harus minimal 8 karakter", result['errors'])

    def test_missing_uppercase(self):
        result = validate_password("password1!")
        self.assertFalse(result['is_valid'])
        self.assertIn("Password harus mengandung huruf besar", result['errors'])

    def test_missing_special_character(self):
        result = validate_password("Password1")
        self.assertFalse(result['is_valid'])
        self.assertIn("Password harus mengandung karakter spesial (!@#$%^&*)", result['errors'])


class PricingTests(TestCase):
    def test_calculate_normal_discount(self):
        self.assertEqual(calculate_discount(100000, 20), 80000)

    def test_calculate_full_discount(self):
        self.assertEqual(calculate_discount(100000, 100), 0)

    def test_invalid_discount_raises_error(self):
        with self.assertRaises(ValueError):
            calculate_discount(100000, 150)
