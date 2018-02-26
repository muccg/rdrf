
from .main_exporters import Exporter, RegistryExporter, RegistryDefExporter
from .main_importers import ZipFileImporter
from . import definitions


def export_registry(registry_code, filename=None, verbose=False, indented_logs=True):
    exporter = RegistryExporter()
    zipfile = exporter.export(
        registry_code,
        filename=filename,
        verbose=verbose,
        indented_logs=indented_logs)
    return zipfile


def export_registry_definition(registry_code, filename=None, verbose=False, indented_logs=True):
    exporter = RegistryDefExporter()
    zipfile = exporter.export(
        registry_code,
        filename=filename,
        verbose=verbose,
        indented_logs=indented_logs)
    return zipfile


def export_cdes(filename=None, verbose=False, indented_logs=True):
    filename = filename or 'exported_CDEs.zip'
    exporter = Exporter.create(definitions.CDE_EXPORT_DEFINITION)
    zipfile = exporter.export(filename=filename, verbose=verbose, indented_logs=indented_logs)
    return zipfile


def export_refdata(filename=None, verbose=False, indented_logs=True):
    filename = filename or 'exported_reference_data.zip'
    exporter = Exporter.create(definitions.REFDATA_EXPORT_DEFINITION)
    zipfile = exporter.export(filename=filename, verbose=verbose, indented_logs=indented_logs)
    return zipfile


def inspect_zipfile(zipfile):
    importer = ZipFileImporter(zipfile)
    importer.inspect()


def import_zipfile(
        zipfile,
        import_type=None,
        verbose=False,
        indented_logs=True,
        simulate=False,
        force=False):
    importer = ZipFileImporter(zipfile)
    importer.do_import(import_type=import_type, verbose=verbose,
                       indented_logs=indented_logs, simulate=simulate, force=force)
