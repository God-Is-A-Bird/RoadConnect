from model import __version__, __license__ , __author__, __email__, __secondary_email__

def main():
    print(f"Welcome to RoadConnect version {__version__}.")
    print(f"This program has been written by {__author__} ({__email__}, or {__secondary_email__}) as part of an undergraduate capstone research project at the University of Texas at Austin.")
    print(f"This version of the program is licensed under {__license__}.")
    print(f"Thank you to Professor Carlos E. Ramos Scharrón for his mentorship and the foundational field studies that supported this research.")
    print(f"Thank you to Protectores de Cuencas Inc. for supporting me in this project with a stipend.")

if __name__ == '__main__':
    main()
