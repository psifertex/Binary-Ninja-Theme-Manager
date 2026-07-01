# A Theme Manager For Binary Ninja

> Developed for Binary Ninja 5.3

A simple plugin for browsing, installing, and applying community `.bntheme` themes inside Binary Ninja.

## Preview

![Theme Manager](rsc/image.png)

## What it does

- Lists themes from configured GitHub repositories, grouped in a collapsible list
- Shows installed themes locally
- Live preview of a theme — a sample linear view and flow graph rendered with the
  theme's own colors, before you apply it (remote themes are fetched on demand)
- Installs and applies themes directly from the UI
- Search/filter with a quick-clear button

## Storage

Installed themes are saved under Binary Ninja's user directory (platform-dependent),
in the `community-themes/` subfolder — e.g. on Linux:

```
~/.binaryninja/community-themes/
```

## Usage

Open:

```
Plugins → Theme Manager
```

Then:
- **Select** a theme in the list to preview it
- Click **Install** to download a remote theme, or **Set Active** to apply an
  installed one (may need restart)

## Supported repos

- Vector35 – community themes  
  https://github.com/Vector35/community-themes

- Catppuccin – Binary Ninja themes  
  https://github.com/catppuccin/binary-ninja/tree/main/themes

- Dracula – Binary Ninja theme  
  https://github.com/dracula/binary-ninja

- Evan Richter – Base16 Binary Ninja colors  
  https://github.com/evanrichter/base16-binary-ninja

- FuzzySecurity – Binary Ninja themes  
  https://github.com/FuzzySecurity/BinaryNinja-Themes

## Requirements

- Binary Ninja 5.3+
- Internet access for fetching themes

