## Plugin that shows a number in 10, 16, 2 and 8 numeral systems for Sublime 3

This plugin converts the selected number in decimal, hexadecimal, binary or octal numeral systems and displays a popup that shows the result in all four (dec, hex, bin and oct) numeral systems. There is three modes of popup window:

*basic*

![popup example](screenshot_basic.png "popup basic example")

*extended*

![popup example](screenshot_extended.png "popup extended example")

*tabled*

![popup example](screenshot_tabled.png "popup tabled example")

### Installation
Clone this repository or download zip archive into the Sublime 3 package directory (you can find it in menu option `Preferences -> Browse Packages...`). **Keep in mind** that plugin folder name should be `Display numbers`.

### Additional functionality
* Pressing any digit of binary number makes it opposite of it's current value.
* "swap" button swaps the bit positions what can be useful in some architectures.
* Key binding is available for convert numeral system and swap endianness functions.

### Settings
You can setup this plugin settings or key bindings which can be edited in menu option
`Preferences -> Package Settings -> Display nums -> Settings` or `Key bindings` accordingly.
Or you can define project specific settings by adding "**disnum.**" to the setting option, for example:

*user settings file*
```json
{
    "plugin_mode": "extended"
}
```
*project settings file*
```json
{
    "disnum.plugin_mode": "tabled"
}
```
