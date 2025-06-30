#!/bin/sh
echo "delete backup-files" 
rm -rf ../backup/*
cp -rf ../output/* ../backup/
rm -rf ../output/*

echo "finish backuping" 