name: Build Windows EXE

on:
  push:
    branches: [ "main" ]
  workflow_dispatch:

jobs:
  build:
    runs-on: windows-latest

    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install pyinstaller
          if exist requirements.txt pip install -r requirements.txt

      - name: Build EXE
        run: |
          pyinstaller --onefile game/game.py

      - name: Upload EXE
        uses: actions/upload-artifact@v4
        with:
          name: game-exe
          path: dist/*.exe
