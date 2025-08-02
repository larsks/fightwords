#!/bin/sh

tmpdir=$(mktemp -d ./wordsXXXXXX)
trap 'rm -rf $tmpdir' EXIT
split -l5 words.txt "$tmpdir/words-"
find "$tmpdir" -type f -print0 |
  xargs -n1 -P0 -r -0 uv run fight_word_generator.py \
    --font "Super Frosting,Badaboom BBMore JanuaryFirst DrawRetro Podcast,DINOUS,Besty Land,Green Town" \
    --negate
