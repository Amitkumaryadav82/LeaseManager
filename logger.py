import logging

def getLogger():
   logger= logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
   return logger
