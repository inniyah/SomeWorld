rem del /F /S /Q dist
del /F /S /Q MANIFEST
del /F /Q /S *.pyc
del /F /Q /S *.pyo
del /F /Q /S doc/html

cd doc
call make.bat html

cd ..
python setup.py sdist
pause