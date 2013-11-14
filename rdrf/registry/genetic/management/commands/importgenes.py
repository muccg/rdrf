from django.core.management.base import BaseCommand
from django.db import transaction
from optparse import make_option


# Default URL to attempt the download from.
HGNC_GENENAMES_URL = "http://www.genenames.org/cgi-bin/hgnc_downloads.cgi?title=HGNC+output+data&hgnc_dbtag=onlevel=pri&=on&order_by=gd_app_sym_sort&limit=&format=text&.cgifields=&.cgifields=level&.cgifields=chr&.cgifields=status&.cgifields=hgnc_dbtag&&where=&status=Approved&status_opt=1&submit=submit&col=gd_hgnc_id&col=gd_app_sym&col=gd_app_name&col=gd_status&col=gd_prev_sym&col=gd_aliases&col=gd_pub_chrom_map&col=gd_pub_acc_ids&col=gd_pub_refseq_ids"


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option("--flush", action="store_true", dest="flush", help="Flush genes before importing"),
    )
    help = "Imports genes in HGNC format."
    args = "[HGNC tab delimited file/URL]"

    @transaction.commit_manually
    def handle(self, *args, **options):
        from registry.genetic.models import Gene
        from registry.humangenome import hgnc

        if len(args) == 0:
            args = [HGNC_GENENAMES_URL]

        flush = options.get("flush", False)

        if flush:
            print "Flushing existing gene data:",
            Gene.objects.all().delete()
            transaction.commit()
            print "done."

        for input in args:
            try:
                print (input + ":"),

                data = hgnc.open(input)
                for record in data.get_record():
                    gene = Gene()
                    gene.symbol = record["approved symbol"]
                    gene.hgnc_id = record["hgnc id"]
                    gene.name = record["approved name"] if "approved name" in record else ""
                    gene.status = record["status"] if "status" in record else ""
                    gene.chromosome = record["chromosome"] if "chromosome" in record else ""
                    gene.accession_numbers = record["accession numbers"] if "accession numbers" in record else ""
                    gene.refseq_id = record["refseq ids"] if "refseq ids" in record else ""
                    gene.save()

                transaction.commit()

                print "done."
            except hgnc.HeaderError, e:
                print "ERROR: Malformed file."
            except Exception, e:
                print "ERROR: %s" % e
