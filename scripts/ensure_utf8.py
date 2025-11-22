import argparse
import sys
import charset_normalizer


def ensure_utf8(filename):
    try:
        # First try to read as UTF-8
        with open(filename, "r", encoding="utf-8") as f:
            f.read()
        return False
    except UnicodeDecodeError:
        pass
    except Exception as e:
        print(f"Error reading {filename}: {e}")
        return False

    # If failed, try to detect encoding
    try:
        with open(filename, "rb") as f:
            content = f.read()

        matches = charset_normalizer.from_bytes(content)
        best_match = matches.best()

        if not best_match:
            print(f"Could not detect encoding for {filename}")
            return True

        # Decode with detected encoding and re-encode as UTF-8
        text = content.decode(best_match.encoding)
        with open(filename, "w", encoding="utf-8") as f:
            f.write(text)

        print(f"Converted {filename} from {best_match.encoding} to utf-8")
        return True

    except Exception as e:
        print(f"Error converting {filename}: {e}")
        return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("filenames", nargs="*", help="Filenames to check")
    args = parser.parse_args()

    ret_code = 0
    for filename in args.filenames:
        if ensure_utf8(filename):
            ret_code = 1

    return ret_code


if __name__ == "__main__":
    sys.exit(main())
