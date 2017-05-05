#!/bin/bash

#   Generator - a Inkscape extension to generate end-use files from a model
#   Copyright (C) 2008  Aurélio A. Heckert
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.

#   Version 0.4

# Collect all args and create local variables:
for arg in "$@"; do
  if ( echo -n $arg | grep -q '^--.*=' ); then
    key="$( echo -n "$arg" |
            sed 's/^--\([^=]*\)=.*$/\1/; s/[^a-zA-Z0-9]/_/' )"
    val="$( echo -n "$arg" |
            sed 's/^--\([^=]*\)=\(.*\)$/\2/' )"
    eval "$key=\"$val\""
  else
    svg_file="$arg"
  fi
done

if ! zenity --version 2>/dev/null; then
  function zenity() {
    echo -e "\n$@\n" >&2
  }
  zenity "You must to install Zenity to have a better interaction
with this script, but it will work anyway."
fi

if [ "${data_file:0:1}" != "/" ]; then
  data_file="$(pwd)/$data_file"
fi

if ! test -f "$data_file"; then
  zenity --error --title="User Information Error" \
         --text="The CSV file \"$data_file\" was not found.

Please, give the right name, or give the full path for the CSV file."
  exit 1
fi

function sep_line {
  sed 's/^\([^"]*\("[^"]*"[^"]*\)*"[^"]*\),/\1#COMMAHACK#/g' |
  sed 's/,/\n/g' | sed "s/\"\"/\"/g; s/^['\"]\|['\"]$//g"
}

# Set column names:
eval "$(
  col=0
  head --lines=1 "$data_file" | sep_line |
  while read name; do
    let col++
    if [ "$var_type" == "name" ]; then
      echo col_name[$col]=$( echo $name | sed "s/[][ \$'\"]/_/g" )
    else
      echo col_name[$col]=$col
    fi
    echo tot_col=$col
  done
)"

# '

eval "$(
  echo "$extra_vars" | sed 's/|/\n/g' |
  while read extra; do
    key="$( echo "$extra" | sed 's/^.*=>\(.*\)$/\1/g' )"
    for i in $( seq $tot_col ); do
      if [ "${col_name[$i]}" = "$key" ]; then
        echo extracol[$i]="'$( echo "$extra" | sed 's/^\(.*\)=>.*$/\1/g' )'"
      fi
    done
  done
)"

if [ "$preview" = "true" ]; then
  # debug:
  txt=''
  for i in $( seq $tot_col ); do
    txt="$txt\n%VAR_${col_name[$i]}%"
  done
  for i in $( seq $tot_col ); do
    [ "${extracol[$i]}" != "" ] && txt="$txt\n${extracol[$i]}"
  done
  zenity --info --title="Generator Variables" \
         --text="The replaceable text, based on your configuration and on the CSV are:\n$txt"
fi

eval "output=\"$output\""

[ "$( dirname "$output" )" != "" ] && mkdir --parents "$( dirname "$output" )"

[ "$format" = "" ] && format=PDF
format=$( echo $format | tr a-z A-Z )

if ! ( echo "$output" | grep -qi "$format\$" ); then
  if zenity --question --text="
Your output pattern has a file extension diferent from the export format.

Did you want to add the file extension?"; then
    output="$output.$( echo $format | tr A-Z a-z )"
  fi
fi

tmp_svg=$( mktemp )
tmp_png=$( mktemp )
ink_error=$( mktemp )

my_pid=$$
function the_end {
  rm $tmp_svg $tmp_png $ink_error
  kill $my_pid
}

function ink-generate {
  f="$( echo "$1" | sed 's/^[^=]*=\(.*\)$/\1/' )"
  rm "$f" 2>/dev/null
  ( inkscape --without-gui \
             "$1" --export-dpi="$dpi" \
             $tmp_svg 2>&1 ) > $ink_error
  if ! test -f "$f"; then
    zenity --error --title="Inkscape Converting Error" \
           --text="$(cat $ink_error |
                     sed 's/&/&amp;/g; s/</&lt;/g; s/>/&gt;/g' )"
    the_end
    exit 1
  fi
}

function show_preview {
  case $format in
    SVG)
      ( inkview "$1" || inkscape "$1" ) 2>/dev/null ||
      echo 'There is no visualizator for SVG' >&2 ;;
    PDF)
      ( evince "$1" || kpdf "$1" || xpdf "$1" || gs "$1" ) 2>/dev/null ||
      echo 'There is no visualizator for PDF' >&2 ;;
    PS)
      ( evince "$1" || gs "$1" ) 2>/dev/null ||
      echo 'There is no visualizator for PS'  >&2 ;;
    EPS)
      ( evince "$1" || gs "$1" ) 2>/dev/null ||
      echo 'There is no visualizator for EPS' >&2 ;;
    PNG)
      ( eog "$1" || kview "$1" || display "$1" ) 2>/dev/null ||
      echo 'There is no visualizator for PNG' >&2 ;;
    JPG)
      ( eog "$1" || kview "$1" || display "$1" ) 2>/dev/null ||
      echo 'There is no visualizator for JPG' >&2 ;;
  esac
  echo 100
  the_end
}

tot_lines=$( wc --lines "$data_file" | sed 's/^\([0-9]\+\).*/\1/' )
if [ "$var_type" == "name" ]; then
  let tot_lines--
fi

cur_line=0

cat "$data_file" | (
  [ "$var_type" == "name" ] && read cut_frist_line
  while read line; do
    col=0
    replace="$(
      echo "$line" | sep_line |
      while read val; do
        let col++
        echo -n "s/%VAR_${col_name[$col]}%/$(
                 echo "$val" | sed "s/\//\\\\\//g; s/'/\´/g"
                 )/g; " | sed 's/#COMMAHACK#/,/g'
        if [ "${extracol[$col]}" != "" ]; then
          echo -n "s/${extracol[$col]}/$(
                   echo "$val" | sed "s/\//\\\\\//g; s/'/\´/g"
                   )/g; " | sed 's/#COMMAHACK#/,/g'
        fi
      done
    )"
    eval "sed '$replace' '$svg_file' > $tmp_svg"
    out_file="$( echo "$output" | sed "$replace" )"
    #echo "Gerando $out_file ..."
    case $format in
      SVG)
        cp "$tmp_svg" "$out_file" ;;
      PDF)
        ink-generate --export-pdf="$out_file" ;;
      PS)
        ink-generate --export-ps="$out_file" ;;
      EPS)
        ink-generate --export-eps="$out_file" ;;
      PNG)
        ink-generate --export-png="$out_file" ;;
      JPG)
        ink-generate --export-png="$tmp_png"
        if ! ( echo "$output" | grep -qi '.jpe\?g$' ); then
          output="$output.jpg"
        fi
        convert $tmp_png "$out_file" ;;
    esac
    let cur_line++
    echo $(( ( $cur_line * 100 ) / $tot_lines ))
    [ "$preview" = "true" ] && show_preview "$out_file" && exit 0
  done |
  zenity --progress --title="Generator" \
         --text="Generating..." --auto-close --width=400
)

[ "$preview" = "true" ] && exit 0

the_end
