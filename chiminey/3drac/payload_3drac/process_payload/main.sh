#!/bin/sh
# version 2.0

INPUT_DIR=$1
OUTPUT_DIR=$2

JAVA_HOME=/opt/jdk1.8.0_101

cp app3.jar $INPUT_DIR/app3.jar

cp transform-image.jar $INPUT_DIR/transform-image.jar

cp transform.jar $INPUT_DIR/transform.jar
cp createImage.jar $INPUT_DIR/createImage.jar

cp roughness-analysis-cli.jar $INPUT_DIR/roughness-analysis-cli.jar
cp run-rac.py $INPUT_DIR/run-rac.py
cd $INPUT_DIR


python run-rac.py -v values -o ../$OUTPUT_DIR -j $JAVA_HOME

# --- EOF ---
