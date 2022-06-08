# camcoremerge.py

Combines multiple PDF files into a signle PDF file, while preserving the page order.

Works on ZIP's from cambridge core.

## Usage

1. "Select All"
2. "Download PDF (zip)"
3. `./camcoremerge.py ../../cambridge-core_modern-compiler-implementation-in-ml_8Jun2022/ ./mci-ml.pdf`

## Credits

- The roman numeral parsing is based on [Paul M. Winkler's code from the python cook book](https://www.oreilly.com/library/view/python-cookbook/0596001673/ch03s24.html)
- The core PDF maniplation is handlded by [`pdfrw`](https://github.com/pmaupin/pdfrw) by Patrick Maupin
- PDF Label maniplations in copied from [`pagelabels-py`](https://github.com/lovasoa/pagelabels-py) by Ophir LOJKINE.

## License

GPL v3
