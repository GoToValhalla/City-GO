from data.scripts.collect_osm_zelenogradsk import collect_places


def main() -> None:
    result = collect_places()
    print(f"Saved OSM raw and seed payload: raw={result['raw_elements']} seed={result['seed_items']}")


if __name__ == "__main__":
    main()
