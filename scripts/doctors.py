from registry.patients.models import Doctor, State
import sys
import json
import django

django.setup()


class DoctorExporter(object):
    def __init__(self, json_filename):
        self.json_filename = json_filename
        self.doctors = []

    def export(self):
        for doctor in Doctor.objects.all():
            d = {}
            d["family_name"] = doctor.family_name
            d["given_names"] = doctor.given_names
            d["surgery_name"] = doctor.surgery_name
            d["speciality"] = doctor.speciality
            d["address"] = doctor.address
            d["suburb"] = doctor.suburb
            if doctor.state:
                d["state"] = {
                    "short_name": doctor.state.short_name,
                    "name": doctor.state.name,
                    "country_code": doctor.state.country_code}
            else:
                d["state"] = None

            d["phone"] = doctor.phone
            d["email"] = doctor.email
            self.doctors.append(d)
            with open(self.json_filename, "w") as f:
                json.dump(self.doctors, f)
            print("exported %s OK" % d)

    def do_import(self):
        with open(self.json_filename) as f:
            self.doctors = json.load(f)
        for d in self.doctors:
            doctor = Doctor()
            doctor.family_name = d["family_name"]
            doctor.given_names = d["given_names"]
            doctor.surgery_name = d["surgery_name"]
            doctor.speciality = d["speciality"]
            doctor.address = d["address"]
            doctor.suburb = d["suburb"]
            doctor.phone = d["phone"]
            doctor.email = d["email"]
            if d["state"]:
                try:
                    s = d["state"]
                    state, created = State.objects.get_or_create(short_name=s["short_name"])
                    if created:
                        state.name = s["name"]
                        if s["name"] == "New Zealand":
                            state.country_code = "NZ"
                        else:
                            state.country_code = "AU"

                        state.save()

                    doctor.state = state
                except State.DoesNotExist:
                    print("no state for doctor %s %s: state = %s" % (d["given_names"], d["family_name"], d["state"]))
            doctor.save()


if __name__ == "__main__":
    cmd = sys.argv[1]
    filename = sys.argv[2]
    exporter = DoctorExporter(filename)

    if cmd == "export":
        exporter.export()
    elif cmd == "import":
        exporter.do_import()
    else:
        print("Usage: python doctors [import|export] json_filename")
        sys.exit(1)
