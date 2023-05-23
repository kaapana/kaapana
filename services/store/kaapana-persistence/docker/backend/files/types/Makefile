all: Instance.schema.json Dataset.schema.json Experiment.schema.json Job.schema.json

%.schema.json: kaapana-objects.yaml
	gen-json-schema -t $(subst .schema.json,,$@) $< | sed 's/https\:\/\/www\.kaapana\.ai\//urn:kaapana:$(subst .schema.json,,$@)/' > $@

clean:
	rm -rf *.schema.json

