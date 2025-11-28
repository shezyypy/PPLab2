import re
import argparse
import sys
from typing import List
import requests

# Каждый октет состоит из: 25[0-5] (250-255) | 2[0-4]\d (200-249) | 1\d{2} (100-199) | [1-9]?\d
# Полный IPv4 состоит из 4 октетов, разделенных точками
IPV4_OCTET = r'(?:25[0-5]|2[0-4]\d|1\d{2}|[1-9]?\d)'
IPV4_REGEX = re.compile(rf'\b{IPV4_OCTET}(?:\.{IPV4_OCTET}){{3}}\b')


headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/118.0.5993.90 Safari/537.36"
}

def is_valid_ipv4(ip: str) -> bool:
    """Возвращает True если IPv4"""
    if not isinstance(ip, str):
        return False
    return bool(IPV4_REGEX.fullmatch(ip.strip()))


def find_ipv4_in_text(text: str) -> List[str]:
    """Ищет все IPv4 в тексте и выводит их списком"""
    if text is None:
        return []
    return IPV4_REGEX.findall(text)


def extract_from_url(url: str, headers=headers, timeout: int = 8) -> str:
    """Проверка html на присутствие IPv4"""
    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        raise RuntimeError(f"Ошибка при выборе URL {url}: {e}")


def extract_from_file(path: str, encoding: str = 'utf-8') -> str:
    """Читаем контент из файла и возвращаем текст"""
    with open(path, 'r', encoding=encoding, errors='replace') as f:
        return f.read()


def cli_main(argv=None):
    p = argparse.ArgumentParser(description='IPv4 validator and extractor')
    p.add_argument('--mode', choices=['user', 'url', 'file'], default='user',
                   help='Режим ввода: user (интерактив), url (выборка), file (пользовательский файл)')
    p.add_argument('--source', help='Для URL или файлов: URL or file path')
    p.add_argument('--test', action='store_true', help='Начать unit tests')
    args = p.parse_args(argv)

    if args.test:
        run_tests()
        return

    if args.mode == 'user':
        text = input('Введи string чтобы найти IPv4 адрес: ').strip()
        ips = IPV4_REGEX.findall(text)
        if ips:
            print('Найдены IPv4 адреса:')
            for ip in ips:
                print('-', ip)
        else:
            print('Нет верных IPv4 адресов.')

    elif args.mode == 'url':
        if not args.source:
            print('Error: --source URL нужно указать действующий URL адрес', file=sys.stderr)
            sys.exit(2)
        try:
            content = extract_from_url(args.source)
        except Exception as e:
            print('Не получилось извлечь из URL:', e, file=sys.stderr)
            sys.exit(1)
        ips = IPV4_REGEX.findall(content)
        if ips:
            print(f'Найдены {len(ips)} IPv4 адреса в этом URL:')
            for ip in ips:
                print('-', ip)
        else:
            print('Не найдены IPv4 адреса в этом URL.')

    elif args.mode == 'file':
        if not args.source:
            print('Error: --source <file path> требуется путь к файлу', file=sys.stderr)
            sys.exit(2)
        try:
            content = extract_from_file(args.source)
        except Exception as e:
            print('ОШибка при чтении файла:', e, file=sys.stderr)
            sys.exit(1)
        ips = IPV4_REGEX.findall(content)
        if ips:
            print(f'Найдены {len(ips)} IPv4 адреса в файле:')
            for ip in ips:
                print('-', ip)
        else:
            print('Не найдено IPv4 адресов в этом файле.')


# Unit tests
import unittest

class TestIPv4Regex(unittest.TestCase):

    def test_valid_ips(self):
        valid = [
            '0.0.0.0',
            '127.0.0.1',
            '1.2.3.4',
            '192.168.1.1',
            '255.255.255.255',
            '10.0.0.254',
            '99.99.99.99'
        ]
        for ip in valid:
            with self.subTest(ip=ip):
                self.assertTrue(is_valid_ipv4(ip), msg=f'{ip} should be valid')

    def test_invalid_ips(self):
        invalid = [
            '',
            '256.0.0.1',    # октет >255
            '192.168.1',    # всего 3 октета
            '192.168.1.1.1',
            '192.168.01.1',
            'abc.def.ghi.jkl',
            '1234.5.6.7',
            '1.2.3.-4',
            '1.2.3.256'
        ]
        for ip in invalid:
            with self.subTest(ip=ip):
                self.assertFalse(is_valid_ipv4(ip), msg=f'{ip} should be invalid')

    def test_find_ipv4_in_text(self):
        text = 'Client 192.168.0.10 connected from 10.0.0.1; failed at 256.1.1.1 and 8.8.8.8.'
        found = IPV4_REGEX.findall(text)
        found = find_ipv4_in_text(text)
        self.assertIn('192.168.0.10', found)
        self.assertIn('10.0.0.1', found)
        self.assertIn('8.8.8.8', found)
        self.assertNotIn('256.1.1.1', found)


    def test_boundary_values(self):
        self.assertTrue(is_valid_ipv4("0.0.0.0"))
        self.assertTrue(is_valid_ipv4("255.255.255.255"))

    def test_invalid_boundary_values(self):
        self.assertFalse(is_valid_ipv4("255.255.255.256"))
        self.assertFalse(is_valid_ipv4("-1.2.3.4"))

    def test_ips_in_html(self):
        text = "<div>Server at <b>172.16.0.1</b> responded. Backup: <span>8.8.4.4</span></div>"
        found = find_ipv4_in_text(text)
        self.assertIn("172.16.0.1", found)
        self.assertIn("8.8.4.4", found)

    def test_ips_with_noise(self):
        text = "Random strings x1.2.3.4y but valid 1.2.3.4 inside"
        found = find_ipv4_in_text(text)
        self.assertEqual(found, ["1.2.3.4"])


def run_tests():
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestIPv4Regex)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if not result.wasSuccessful():
        sys.exit(1)


if __name__ == '__main__':
    cli_main()
