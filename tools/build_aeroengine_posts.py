from __future__ import annotations

"""Build the aeroengine briefing column through the shared static-blog renderer.

The shared renderer owns homepage, archive, taxonomy, search and sidebar updates.
Keeping this small entry point gives the aeroengine automation an independent,
stable command without duplicating those cross-site transformations.
"""

from build_aircraft_posts import main


if __name__ == "__main__":
    main()
