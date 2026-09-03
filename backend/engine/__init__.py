"""Deployment engine abstraction.

`base.py` defines the `DeploymentEngine` seam; everything above it (routers)
speaks `TopologyData`, everything below is engine-specific (currently Kathara).
`networking.py` holds the engine-agnostic topology-to-lab-plan logic.
"""
