#!/usr/bin/env python3
"""
Script to create test files of various sizes for testing the protocol
"""
import os
import random
import string


def create_text_file(filename: str, size_kb: int):
    """Create a text file with random content"""
    size_bytes = size_kb * 1024
    
    with open(filename, 'w') as f:
        chars_written = 0
        while chars_written < size_bytes:
            line_length = min(80, size_bytes - chars_written)
            line = ''.join(random.choices(string.ascii_letters + string.digits + ' ', k=line_length))
            f.write(line + '\n')
            chars_written += line_length + 1
    
    print(f"Created {filename} ({size_kb} KB)")


def create_binary_file(filename: str, size_kb: int):
    """Create a binary file with random content"""
    size_bytes = size_kb * 1024
    
    with open(filename, 'wb') as f:
        f.write(os.urandom(size_bytes))
    
    print(f"Created {filename} ({size_kb} KB)")


def main():
    os.makedirs('test_files', exist_ok=True)
    
    create_text_file('test_files/small.txt', 1)
    create_text_file('test_files/medium.txt', 10)
    create_text_file('test_files/large.txt', 100)
    
    create_binary_file('test_files/small.bin', 1)
    create_binary_file('test_files/medium.bin', 10)
    create_binary_file('test_files/large.bin', 100)
    
    print("\nTest files created in 'test_files/' directory")


if __name__ == '__main__':
    main()

