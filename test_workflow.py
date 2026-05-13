#!/usr/bin/env python
"""Test script to diagnose preview panel issues."""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
import cv2
from models.workflow_graph import WorkflowGraph

# Create a test image
test_image = np.ones((256, 256, 3), dtype=np.uint8) * 128
print(f"Created test image: shape={test_image.shape}, dtype={test_image.dtype}")

# Create workflow
graph = WorkflowGraph()

# Add nodes
input_node = graph.add_node("input_image")
input_node.set_image(test_image)
print(f"Added InputImageNode: {input_node.node_id}, _cache={input_node._cache is not None}")

gaussian_node = graph.add_node("gaussian_blur")
print(f"Added GaussianBlurNode: {gaussian_node.node_id}")

output_node = graph.add_node("output_image")
print(f"Added OutputImageNode: {output_node.node_id}")

# Connect nodes
print("\nConnecting nodes...")
graph.connect(input_node.node_id, gaussian_node.node_id)
print(f"  Connected {input_node.node_id} -> {gaussian_node.node_id}")

graph.connect(gaussian_node.node_id, output_node.node_id)
print(f"  Connected {gaussian_node.node_id} -> {output_node.node_id}")

print(f"\nGraph has {len(graph.nodes)} nodes and {len(graph.edges)} edges")

# Check topological sort
order = graph._topological_sort()
print(f"Topological order: {order}")

# Execute graph
print("\nExecuting graph...")
results = graph.execute()

print(f"\nExecution results:")
for node_id, output in results.items():
    if output is not None:
        print(f"  {node_id}: shape={output.shape}, dtype={output.dtype}")
    else:
        print(f"  {node_id}: None")

# Check if output node has result
if output_node.node_id in results:
    output_data = results[output_node.node_id]
    print(f"\nOutput node result: shape={output_data.shape}, dtype={output_data.dtype}")
    print(f"Output sample values: min={output_data.min()}, max={output_data.max()}, mean={output_data.mean():.1f}")
else:
    print(f"\nERROR: Output node not in results!")

print("\nTest complete.")
