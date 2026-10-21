import wfdb
record = wfdb.rdrecord(r"C:\Users\PC\Documents\bidmc-ppg-and-respiration-dataset-1.0.0\bidmc01")
print(record.sig_name)