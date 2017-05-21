[Hier geht's zur deutschen Version](README-de.md)

This is a reimplementation of the Inkscape generator plugin by Aurélio A.
Heckert, which can be found here:
<http://wiki.colivre.net/Aurium/InkscapeGenerator>

I did this for two reasons:

* It's difficult to run the original extension on Windows, since it is
implemented as a bash script and uses commands like `head` or `sed`. The new
implementation is done in Python and uses only standard features of Python and
Windows.
* The original extension has problems with correct parsing of CSV files when it
comes to characters like "`,`" or "`"`".

#Installation

##Windows

Copy `generator.inx` and `generator.py` to
`C:\Program files\Inkscape\share\extensions`
(global installation) or
`C:\Users\<Username>\Application Data\Roaming\inkscape\share\extension`
(single user installation).

This extension needs Python 2.7, which is shipped with Inkscape 0.92.1 or later.

The following is **NOT** available on Windows:

* Progress bar and cancel button during generation process
* Output to JPEG format

If you want JPEG output, you can install ImageMagick and modify the
`Png_to_jpg` function in `generator.py` as follows (replace
"`Path\to\convert.exe`" with the correct path to the `convert` executable):

```python
def Png_to_jpg(pngfile, jpgfile):
    Call_or_die(
        [
            'Path\to\convert.exe',
            'PNG:' + pngfile,
            'JPG:' + jpgfile
        ],
        'ImageMagick Converting Error')
```

##GNU/Linux

Copy `generator.inx` and `generator.py` to
`/usr/share/inkscape/extensions`
(global installation) or
`/home/<username>/.config/inkscape/extensions/`
(single user installation).

The following software is requires:

* Python 2.7
* Zenity (for better user interaction, the script will work without it)
* Convert (from the ImageMagick suite, for JPEG export)

# Incompatible changes

Some details of the usage of this extension differ from the usage of the
original extension:

* In the Bash-based extension, you had to escape certain characters in your CSV
file. For example, you had to write "`\\\\&amp;`" to get a "`&`". With this
extension, you need to write simply "`&`" (with handling of special characters
enabled) or "`&amp;`" (with handling of special characters disabled).

* In the Bash-based extension, the characters "`[`", "`]`", "`   `", "`$`", "`'`"
and "`"`" were replaced by an underscore if they appear in a column name. For
example, when you have a column named "first name", you had to use
"`%VAR_first_name%`" as placeholder. With this extension, no such replacement
occures. Your have to use the placeholder "`%VAR_first name`".

* This one is only important if you used `generator.sh` not as an inkscape
extension, but called it directly: In the bash script, there were some parameters
with a dash (i.e. "`--data-file`"). In this python script, there are no dashes
in the parameters (i.e. "`--datafile`").
