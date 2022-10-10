# QOI-PyScript
 
QOI-PyScript brings a python implementation of the Quite OK Image format to the web with the PyScript framework.

This project is hosted using GitHub Pages at https://jingram80024.github.io/QOI-PyScript/

This project is currently under development, but this first commit features a functional webpage that allows users to convert between QOI, PNG, and JPEG image formats in the browser. As I am mostly interested in using this as a demonstration of some of the basic capabilities of PyScript, I am not putting any effort into styling the webpage or improving cross-browser compatibility.

Current features being implemented when I have free time:
- Loading icon to show when browser is converting file
- Learning more about asynchronous functions and how to best implement them to keep the page responsive while one thread works on converting the file
- Improving memory performance
- Refactoring code to eliminate repeated code and improve readability
- Addressing issues converting from PNG to JPEG with the A channel in the Pillow Image object