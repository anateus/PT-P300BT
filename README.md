# Printing to a Brother P-Touch Cube PT-P300BT label printer from a computer

A Python-based label printing utility designed for Brother PT-P300BT thermal label printers. This program creates custom labels with text, images, and advanced formatting options, automatically optimizing content to fit within the printer's specifications.

It supports any TrueType and OpenType font, automatically selects the maximum font size to fit the printable area of the tape. Text strings including characters which do not [overshoot](https://en.wikipedia.org/wiki/Overshoot_(typography)) below the [baseline](https://en.wikipedia.org/wiki/Baseline_(typography)) (e.g., uppercase letters) are automatically printed with a bigger font. In addition, the program calculates the size of the printed tape and the print duration and processes images.

## Introduction

The [Brother P-touch Cube PT-P300BT labelling machine](https://support.brother.com/g/b/producttop.aspx?c=gb&lang=en&prod=p300bteuk) is intended to be controlled from the official Brother P-touch Design&Print 2 app for [Android](https://play.google.com/store/apps/details?id=com.brother.ptouch.designandprint2) and [iOS](https://apps.apple.com/it/app/brother-p-touch-design-print/id1105307806) devices.

This repository provides a command-line tool in pure Python to print from a computer.

## Features

### Text Rendering
- **Unicode Support**: Full UTF-8 character support with optional Unicode escape sequences
- **Custom Fonts**: Support for TrueType (.ttf) and OpenType (.otf) fonts
- **Automatic Font Sizing**: Intelligent font size optimization to fit the printable area
- **Multiline Text**: Support for multi-line labels with configurable line spacing
- **Text Styling**: Configurable fill colors, stroke effects, and text centering
- **Font Scaling**: Manual font size scaling with percentage-based adjustments

### Image Processing
- **Image Integration**: Merge images with text labels
- **PDF Support**: Convert PDF files to images for printing
- **Smart Cropping**: Automatic cropping of white space around image content
- **Aspect Ratio Preservation**: Maintains image proportions while resizing
- **Multiple Image Merge**: Combine multiple images in a single label

### Label Customization
- **Flexible Sizing**: Custom horizontal text stretching to specified millimeter widths
- **Padding Control**: Adjustable horizontal padding and vertical positioning
- **End Margins**: Configurable end margins for label finishing
- **Auto-cutting**: Optional automatic cutting or label boundary marking
- **Chain Printing**: Disable feeding for continuous label chains

### Advanced Features
- **Line Spacing Optimization**: Automatic line spacing adjustment when text doesn't fit
- **Visual Guides**: Optional ruler lines and printable area indicators
- **Binary Conversion**: Optimized image processing with custom thresholding
- **Compression Control**: Optional compression disable for specific printing needs
- **Preview Mode**: View generated images before printing

## Usage

Standard usage: `python3 printlabel.py COM_PORT FONT_NAME TEXT_TO_PRINT`

### Basic Text Label

```
python3 printlabel.py -sl COM7 "arial.ttf" "Lorem Ipsum"
```

or:

```
printlabel.exe COM7 "arial.ttf" "Lorem Ipsum"
```

### Multiline Text Label

Text can be multiline when the text includes "\n" characters. (Use the two characters `\n` in your text to create line breaks). The `--line-spacing` option controls the spacing between lines (default: 1.2, meaning 20% extra space between lines). The font size is automatically calculated to fit all lines within the printable area. The `--center-text` option allows horizontally centering each single line.

```bash
python printlabel.py -sl COM3 arial.ttf "Line 1\nLine 2\nLine 3"
```

## Command Line Arguments

```
usage: printlabel.py [-h] [-u] [-l] [-s] [-c] [-i FILE_NAME] [-M FILE_NAME] [-R FLOAT]
                     [-X DOTS] [-Y DOTS] [-S FILE_NAME] [-n] [-F] [-a] [-m DOTS] [-r] [-C]
                     [--fill-color FILL] [--stroke-fill STROKE_FILL]
                     [--stroke-width STROKE_WIDTH] [--text-size MILLIMETERS]
                     [--font-scale NUMBER] [--h-padding DOTS] [--v-shift DOTS]
                     [-p MULTIPLIER] [-H] [--white-level NUMBER] [--threshold NUMBER]
                     COM_PORT [FONT_NAME] [TEXT_TO_PRINT ...]
```

Required positional arguments

- `COM_PORT`: Serial port for printer communication (e.g., COM3, /dev/ttyUSB0)
- `FONT_NAME`: Path to TrueType or OpenType font file (optional, defaults to arial.ttf)
- `TEXT_TO_PRINT`: Text content for the label (supports multiple arguments)

Optional arguments:

```
  -h, --help            show this help message and exit
  -u, --unicode         Use Unicode escape sequences in TEXT_TO_PRINT.
  -l, --lines           Add horizontal lines for drawing area (dotted red) and tape
                        (cyan).
  -s, --show            Show the created image. (If also using -n, terminate.)
  -c, --show-conv       Show the converted image. (If also using -n, terminate.)
  -i FILE_NAME, --image FILE_NAME
                        Image file to print. If this option is used (legacy mode),
                        TEXT_TO_PRINT and FONT_NAME are ignored.
  -M FILE_NAME, --merge FILE_NAME
                        Merge the image file before the text. Can be used multiple times.
  -R FLOAT, --resize FLOAT
                        With image merge, additionaly resize it (floating point number).
  -X DOTS, --x-merge DOTS
                        With image merge, shift right the image of X dots.
  -Y DOTS, --y-merge DOTS
                        With image merge, shift down the image of Y dots.
  -S FILE_NAME, --save FILE_NAME
                        Save the produced image to a PNG file.
  -n, --no-print        Only configure the printer and send the image but do not send
                        print command.
  -F, --no-feed         Disable feeding at the end of the print (chaining).
  -a, --auto-cut        Enable auto-cutting (or print label boundary on e.g. PT-P300BT).
  -m DOTS, --end-margin DOTS
                        End margin (in dots).
  -r, --raw             Send the image to printer as-is without any pre-processing.
  -C, --nocomp          Disable compression.
  -v, --verbose         Print serial diagnostics and verbose printer status.
  --status-only         Only query and print printer status; do not send image data
                        or print.
  --serial-timeout SERIAL_TIMEOUT
                        Seconds to wait for printer responses. Use 0 to wait
                        forever. (default: 10)
  --macos-rfcomm        On macOS, bypass /dev/cu.* and talk directly to the
                        printer RFCOMM channel.
  --rfcomm-channel RFCOMM_CHANNEL
                        RFCOMM channel to use with --macos-rfcomm. PT-P300BT
                        Serial Port Profile is usually channel 1.
  --print-status-frames PRINT_STATUS_FRAMES
                        Maximum number of status frames to read after sending the
                        print command. (default: 20)
  --cleanup-reset       Send a printer reset during cleanup after a successful job.
                        Disabled by default on macOS Bluetooth serial.
  --fill-color FILL     Fill color for the text (e.g., "white"; default = "black").
  --stroke-fill STROKE_FILL
                        Stroke Fill color for the text (e.g., "black"; default = None).
  --stroke-width STROKE_WIDTH
                        Width of the text stroke (e.g., 1 or 2).
  --text-size MILLIMETERS
                        Horizontally stretch the text to fit the specified size.
  --font-scale NUMBER   Scale font size by specified percentage (default: 100%)
  --h-padding DOTS      Define custom left and right horizontal padding in pixels
                        (default: 5 pixels left and 5 pixels right)
  --v-shift DOTS        Define relative vertical translation in pixels (default is to
                        vertically center the font)
  -p MULTIPLIER, --line-spacing MULTIPLIER
                        Line spacing multiplier for multi-line text (default: 1.2)
  -H, --center-text     Horizontally center text inside the label image.
  --white-level NUMBER  Minimum pixel value to consider it "white" when cropping the
                        image. Set it to a value close to 255. (Default: 240)
  --threshold NUMBER    Custom thresholding when converting the image to binary, to
                        manually decide which pixel values become black or white (Default:
                        75)
```

## Usage details

Options `-sln` are useful to simulate the print, showing the created image and adding a ruler in inches and centimeters (magenta), with horizontal lines to mark the drawing area (dotted red) and the tape borders (cyan).

Before generating the text (`TEXT_TO_PRINT`), the tool allows concatenating images with the `-M` option; it can be used more times for multiple images (transparent images are also accepted). The final image can also be saved with the `-S` option and then reused by running again the tool with the `-M` option; when also setting `TEXT_TO_PRINT` to a null string (`""`), the reused image will remain unchanged. Merged images are automatically resized to fit the printable area, removing white borders without modifying the proportion. Resize and translation of merged images can also be manually controlled with `-R` (floating point number), `-X`, `-Y`. The `--text-size` option horizontally stretches or squeezes the text so that it fits the specified size in millimeters; the size parameter includes `--end-margin` and default left and right paddings, but does not include the size of merged images if used, which have a fixed length that has to be kept proportioned. The `font-scale` allows specifying a percentage to scale the font size, maintaining the aspect ratio; font sizes > 100 are accepted even if potentially causing overflow. `--h-padding` and `--v-shift` allow horizontally and vertically translating the text (using `--h-padding` with `--end-margin` enables separately cointrolling left and right margins; specifically `--h-padding` uses the same value for the left and right parts, while `--end-margin` will be a relative value applied to the right `--h-padding`).

`-i` runs the legacy process of *labelmaker.py* and disables image processing.

## Further examples

Example of merging image and text, automatically resizing and translating the image so that it fits the printable area:

```bash
curl https://raw.githubusercontent.com/uroesch/pngpetite/main/samples/pngpetite/happy-sun.png -o resources/happy-sun.png
python printlabel.py -sl -M resources/happy-sun.png COM7 "Gabriola.ttf" "Hello!"
```

Same as before, but uses the PDF version of happy-sun (it is designed for single page PDFs, like barcodes or other custom icons)

```bash
curl https://raw.githubusercontent.com/uroesch/pngpetite/main/samples/pngpetite/happy-sun.png -o resources/happy-sun.png
python printlabel.py -sl -M resources/happy-sun.pdf COM7 "Gabriola.ttf" "Hello!"
```

Same as the happy-sun.png example, but resizing the text so that its length is about 7 centimeters plus heading image, with a small white border at the end:

```bash
python printlabel.py -sl -M resources/happy-sun.png COM7 --text-size 70 --end-margin 10 "micross.ttf" "lorem ipsum dolor sit amet"
```

Examples of usage of Unicode escape sequences:

```bash
python printlabel.py -slnu COM7 "calibri.ttf" "\u2469Note"
```

```bash
python printlabel.py -sl -u COM3 arial.ttf "Caf\u00e9"
```

Examples of using text stroke:

```bash
python printlabel.py -sln --stroke-width 2 -m 10 COM7 "arial.ttf" "Bolded text"
python printlabel.py -sln --stroke-width 1 --fill-color="white" --stroke-fill="black" -m 10 COM7 "Gabriola.ttf" "Text stroke"
```

## Installation

```
git clone https://github.com/Ircama/PT-P300BT && cd PT-P300BT
pip install -r requirements.txt
```

## Code dependency structure

```mermaid
graph LR
    printlabel.py:::highlight --> labelmaker.py
    labelmaker.py --> labelmaker_encode.py
    labelmaker.py --> ptcbp.py
    labelmaker.py --> ptstatus.py

    subgraph Project_Support_Files[Project Support Files]
        requirements[requirements.txt]
        spec[printlabel.spec]
        readme[README.md]
    end

    classDef highlight fill:#ffeb3b,stroke:#fbc02d,stroke-width:3px;
```

## Bluetooth printer connection on Windows

The following steps allow connecting a Windows COM port to the Bluetooth printer.

- Open Windows Settings
- Go to Bluetooth & devices
- Press "View more devices"
- Press "More Bluetooth settings"
- Select "COM Ports" tab
- Press Add... (wait for a while)
- Select Outgoing
- Press Browse...
- Search for PT-P300BT9000 and select it
- Select PT-P300BT9000
- Service: Serial
- Read the name of the COM port
- Press OK
- Press OK

Perform the device pairing.

## Windows Bluetooth Quirk
- As [pytouch-cube](https://github.com/piksel/pytouch-cube) says, for the Brother Cube
  PT-300BT Label Maker:
  > After connecting to the device it will automatically disconnect again.
  - Windows says "Driver Unavailable"
  - But if you simply run the program (under PowerShell), it will work

## Usage on WSL

Pair the printer with an RFCOMM COM port using the Windows Bluetooth panel.

Check the outgoing RFCOMM COM port number and use it to define /dev/ttyS_serial_port_number; for instance, COM5 is /dev/ttyS5.

Usage: `python3 printlabel.py /dev/ttyS_serial_port_number FONT_NAME TEXT_TO_PRINT`

## Bluetooth printer connection on Ubuntu

Connect the printer via [Ubuntu Bluetooth panel](https://help.ubuntu.com/stable/ubuntu-help/bluetooth-connect-device.html.en) (e.g., Settings, Bluetooth).

To read the MAC address: `hcitool scan`. Setup /dev/rfcomm0.

Usage: `python3 printlabel.py /dev/rfcomm0 FONT_NAME TEXT_TO_PRINT`

## Bluetooth printer connection on macOS

Pair the printer in macOS Bluetooth settings first. The system may create a serial device such as `/dev/cu.PT-P300BT2347`, but for this printer that `/dev/cu.*` path can be unreliable after the first print. On macOS, prefer the direct RFCOMM transport:

```bash
uv run python3 printlabel.py \
  --macos-rfcomm \
  /dev/cu.PT-P300BT2347 \
  /path/to/font.otf \
  "Test label"
```

`COM_PORT` is still required with `--macos-rfcomm`, but the script uses it only to infer the paired Bluetooth device name. For example, `/dev/cu.PT-P300BT2347` maps to the paired device `PT-P300BT2347`. If the `/dev/cu.*` device is not currently present, you can still pass the same remembered path as long as the printer is paired.

Useful macOS flags:

- `--macos-rfcomm`: bypasses the macOS `/dev/cu.*` serial driver and opens the printer's Bluetooth RFCOMM channel directly through PyObjC.
- `--rfcomm-channel 1`: selects the RFCOMM channel. The PT-P300BT Serial Port Profile normally uses channel 1, which is the default.
- `--status-only`: queries and prints printer status without sending label image data.
- `--verbose`: prints serial/RFCOMM reads and writes plus verbose printer status frames.
- `--serial-timeout 5`: changes how long to wait for printer responses. Use `0` to wait forever.
- `--print-status-frames 20`: changes how many status frames to wait for after sending the print command.

Example status check:

```bash
uv run python3 printlabel.py \
  --status-only \
  --verbose \
  --macos-rfcomm \
  --serial-timeout 5 \
  /dev/cu.PT-P300BT2347
```

The macOS RFCOMM transport requires `pyobjc-framework-IOBluetooth`, which is included in `pyproject.toml` for macOS installs.

## Creating an executable asset for the GUI

To build an executable file via [pyinstaller](https://pyinstaller.org/en/stable/), first install *pyinstaller* with `pip install pyinstaller`.

The *printlabel.spec* file helps building the executable program. Run it with the following command.

```
pip install pyinstaller  # if not yet installed
pyinstaller printlabel.spec
```

Then run the executable file created in the *dist/* folder.

This repository includes a Windows *printlabel.exe* executable file which is automatically generated by a [GitHub Action](https://github.com/Ircama/PT-P300BT/blob/main/.github/workflows/build.yml). It is packaged in a ZIP file named *printlabel.zip* and uploaded into the [Releases](https://github.com/Ircama/PT-P300BT/releases/latest) folder.

## Notes

The printer has 180 DPI (dot per inch) square resolution at 20 mm/sec.

The max. length of the printable area is 0,499 m.

Even if the Brother TZe tape size is 12 mm, the height of the printable area is 64 pixels, which is 9 mm at 180 DPI: 64 pixels / 180 DPI / 0.0393701 inch/mm = 9 mm.

On this printer, tape is wasted before and after the printable area on each label (about 2.5 cm of additional tape before the printed area and about 1 mm after it).

## History

This repository is based on the scripts included in the following Gists:

- [PT-P300BT Gist](https://gist.github.com/Ircama/bd53c77c98ecd3d7db340c0398b22d8a)
- [dogtopus/Pipfile Gist](https://gist.github.com/dogtopus/64ae743825e42f2bb8ec79cea7ad2057)
- [stecman Gist](https://gist.github.com/stecman/ee1fd9a8b1b6f0fdd170ee87ba2ddafd)
- [vsigler Gist](https://gist.github.com/vsigler/98eafaf8cdf2374669e590328164f5fc)

The scripts convert text labels to appropriate images (including the first page of a PDF conversion with "pdf2image" and which requires poppler to be installed) compatible with 12mm width craft tapes like [TZe-131](https://www.brother-usa.com/products/tze131) or [TZe-231](https://www.brother-usa.com/products/tze231), tuned for the max allowed character size with this printer, regardless the used font. The scripts also include the code to drive the printer via serial Bluetooth interface.

Comparing this repository with the PT-P300BT Gist, the Python *printlabel.py* program has been introduced, replacing *printlabel.cmd* and *printlabel.sh* with several enhancements; it avoids creating temporary image files, provides more accurate image processing and does not rely on ImageMagick. In addition, all options included in the original *labelmaker.py* module are available, with several extensions.

## Other resources

- https://github.com/piksel/pytouch-cube
- https://github.com/probonopd/ptouch-770
- https://github.com/kacpi2442/labelmaker

## Acknowledgments

[stecman](https://gist.github.com/stecman) and his [Gist](https://gist.github.com/stecman/ee1fd9a8b1b6f0fdd170ee87ba2ddafd).
