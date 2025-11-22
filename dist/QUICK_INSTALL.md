# Macolint - Quick Install Commands

One-line installation commands for all supported package managers:

## macOS / Linux

**Homebrew (Custom Tap)**
```bash
brew tap p4puniya/macolint && brew install macolint
```

**Homebrew (Core)**
```bash
brew install macolint
```

**Cargo Install**
```bash
cargo install macolint
```

## Windows

**Scoop**
```powershell
scoop install macolint
```

**Winget**
```powershell
winget install Macolint.Macolint
```

## Arch Linux

**AUR (yay)**
```bash
yay -S macolint
```

**AUR (paru)**
```bash
paru -S macolint
```

## Manual Installation

**Download Binary**
1. Visit: https://github.com/p4puniya/macolint/releases
2. Download for your platform
3. Extract and add to PATH

**Build from Source**
```bash
git clone https://github.com/p4puniya/macolint.git && cd macolint && cargo build --release && cargo install --path .
```

---

For detailed installation instructions and troubleshooting, see [INSTALL.md](INSTALL.md).

