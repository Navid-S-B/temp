import pickle

f = open("cache.pickle", "rb")
info = pickle.load(f)
print(info)