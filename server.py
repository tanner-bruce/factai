from pyfactorio.api.api import FactorioRunner,FactorioClient

if __name__ == '__main__':
    fr = FactorioRunner()
    fr.start()

    fc = FactorioClient()
    fr.add_client(fc)

    fc.observe()