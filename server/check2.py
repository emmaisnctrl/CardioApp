import wfdb
numerics = wfdb.rdrecord(r"C:\Users\PC\Documents\bidmc-ppg-and-respiration-dataset-1.0.0\bidmc01n")
print(numerics.sig_name)