from autocv.app.runtime import create_runtime


def main() -> None:
    runtime = create_runtime()
    runtime.run()


if __name__ == "__main__":
    main()

