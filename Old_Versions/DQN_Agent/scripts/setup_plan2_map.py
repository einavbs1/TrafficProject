"""Build the 4-lane default map and register it as the project default."""

import sys

from pathlib import Path



ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:

    sys.path.insert(0, str(ROOT))



from flowgrid.core.phasing_schemes import PhasingScheme

from flowgrid.maps.map_builder import DEFAULT_FLOWS

from flowgrid.maps.map_registry import (

    DEFAULT_MAP_ID,

    REGISTRY_PATH,

    delete_map,

    list_saved_maps,

    save_map,

)





def main():

    for preset in list(list_saved_maps()):

        delete_map(preset.id)

        print(f"Deleted map: {preset.id}")



    preset = save_map(

        "Default (4-lane intersection)",

        arm_length=500,

        flows=dict(DEFAULT_FLOWS),

        overwrite=True,

        map_id=DEFAULT_MAP_ID,

        phasing_scheme=PhasingScheme.OPPOSITE_THRU_RT_THEN_THRU.value,

        separate_right_turn=True,

        lanes_per_approach=4,

        baseline_through_seconds=60.0,

        baseline_left_to_through_ratio=0.60,

        sync_defaults=True,

    )

    print(f"Created default map: {preset.id}")

    print(f"  sumocfg: {preset.abs_sumocfg()}")

    print(f"  policy:  {preset.abs_policy()}")

    print(f"  phasing: {preset.phasing_scheme}")

    print(f"  lanes:   {preset.lanes_per_approach}")

    print(f"Registry: {REGISTRY_PATH}")





if __name__ == "__main__":

    main()

