#!/bin/bash
LANG="$1"          # e.g. es
EXISTING_PO="$2"   # e.g. /data/old.po
YAML_FILE="$3"     # e.g. /data/mtm.yaml

if [ -d /app/rdrf/scripts ]; then
    SCRIPTS_DIR="/app/rdrf/scripts"
else
    SCRIPTS_DIR="/app/scripts"
fi

echo "Using $SCRIPTS_DIR ..."

TRANSLATION_DIR="/data/translations/locale/$LANG/LC_MESSAGES"

# We need copies of the system po file because the extract html strings
# step clobbers the django po file
TMPFILE1=/tmp/TMPFILE1.po
TMPFILE2=/tmp/TMPFILE2.po
TMPFILE3=/tmp/TMPFILE3.po

echo "removing existing po and mo files for $LANG"
echo "in $TRANSLATION_DIR ..."
cd $TRANSLATION_DIR

rm *.po
rm *.mo

echo "extracting cde labels from $YAML_FILE ..."
django-admin create_translation_file --yaml_file=$YAML_FILE --system_po_file=$EXISTING_PO > $TMPFILE1

echo "extracting html strings from $YAML_FILE ..."
django-admin create_translation_file --yaml_file=$YAML_FILE --extract_html_strings

# this clobbers django.po
cp django.po $TMPFILE2

echo "merging po files into django.po ..."
$SCRIPTS_DIR/merge_pofiles $EXISTING_PO $TMPFILE1 $TMPFILE2 > $TMPFILE3

rm *.po
rm *.mo

echo "updating django.po with merged file ..."
cp $TMPFILE3 django.po

echo "compiling the new django.po file ..."
django-admin compilemessages

echo "copying the new po amd mo file to /data ..."
cp django.mo /data/
cp django.po /data/

find /tmp -name "TMPFILE*.po" -delete






