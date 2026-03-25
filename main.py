import sys
from PySide6.QtWidgets import QApplication

print("STEP 1: before QApplication")

def main():
    app = QApplication(sys.argv)

    print("STEP 2: after QApplication")

    from gui.app import create_app
    print("STEP 3: imported app")

    window = create_app()
    print("STEP 4: window created")

    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()