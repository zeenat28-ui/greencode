import json

m = json.load(open("alexa/addon.json", encoding="utf-8"))
print("manifest", m.get("manifestVersion"))
i = m["integrations"][0]
print("type", i["type"])
print("uri", i["config"]["endpoints"]["default"]["uri"])
print("name", m["storeListing"]["name"]["value"])
print("examplePhrases", len(m["storeListing"].get("examplePhrases", [])))
print("privacy", m["storeListing"]["privacyAndCompliance"]["privacyPolicyUrl"])
