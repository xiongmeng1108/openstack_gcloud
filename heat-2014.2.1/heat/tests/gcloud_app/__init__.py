__author__ = 'Administrator'

def test():
    for k in  xrange(0,5):
        if k==3:
            return k
        print k

if  __name__ == "__main__":
    print "hello"
    a=dict()
    a["a"]=2
    a["b"+str(1)]= a.pop("a")
    print test()



