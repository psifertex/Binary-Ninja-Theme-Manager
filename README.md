# Swatch

> Color themes for Binary Ninja, with a live preview before you switch.

Browse, preview, and apply [`.bntheme`](https://docs.binary.ninja/dev/themes.html)
color themes inside Binary Ninja — both the themes Binary Ninja ships and ones
from community repositories. Every theme renders a sample linear view and flow
graph in its own colors, so you can see it before committing to it.

## Preview

![Swatch](https://github.com/psifertex/Swatch/blob/main/rsc/image.png?raw=true)

## What it does

- Lists themes from configured GitHub repositories, grouped in a collapsible list
- Shows installed themes locally
- Live preview of a theme — a sample linear view and flow graph rendered with the
  theme's own colors, before you apply it (remote themes are fetched on demand)
- Installs and applies themes directly from the UI
- Search/filter with a quick-clear button

## Storage

Installed themes are saved under Binary Ninja's
[user folder](https://docs.binary.ninja/guide/index.html#user-folder), which is
platform-dependent, in the `community-themes/` subfolder — e.g. on Linux:

```
~/.binaryninja/community-themes/
```

Binary Ninja scans both `themes/` and `community-themes/` there, so themes
installed by this plugin are picked up alongside any you cloned yourself.

Writing your own? See [Creating Themes](https://docs.binary.ninja/dev/themes.html)
for the `.bntheme` file format.

## Usage

Open:

```
Plugins → Swatch
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

- Binary Ninja (see `minimumbinaryninjaversion` in `plugin.json` for the minimum build)
- Internet access for fetching themes


## Credits and licensing

Originally created by [Léo BECHET (lele394)](https://github.com/lele394/Binary-Ninja-Theme-Manager)
and published under the MIT license, which this fork continues under. Léo's
copyright notice is retained alongside this fork's, as MIT requires.

In August 2026 the upstream repository replaced its MIT license with terms that
grant no rights and restrict AI-related use of the project. This fork's history
does not include that change — every line of code here predates it and was
published under MIT. If you want the upstream project under its current terms,
follow the link above.
