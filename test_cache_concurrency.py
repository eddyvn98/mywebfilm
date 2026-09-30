import pytest
import os
import threading
import time
import config_manager as cfg

def test_cache_concurrency():
    # Setup: Ensure cache file is initialized
    initial_data = [{"full_path": "dummy1.mp4", "views": 10}, {"full_path": "dummy2.mp4", "views": 5}]
    cfg.save_cache(initial_data)
    
    errors = []
    
    def worker_task(thread_id):
        try:
            for i in range(30):
                # Read Cache
                data = cfg.load_cache()
                assert isinstance(data, list)
                
                # Modify views dynamically
                for item in data:
                    if item["full_path"] == "dummy1.mp4":
                        item["views"] += 1
                        
                # Write Cache
                cfg.save_cache(data)
                
                # Small sleep to yield execution
                time.sleep(0.01)
        except Exception as e:
            errors.append(f"Thread {thread_id} error: {e}")

    # Spawn 10 concurrent threads
    threads = []
    for i in range(10):
        t = threading.Thread(target=worker_task, args=(i,))
        threads.append(t)
        t.start()

    # Wait for all threads to finish
    for t in threads:
        t.join()

    # Assert no errors occurred
    assert len(errors) == 0, f"Errors found during concurrent caching: {errors}"
    
    # Verify values are consistent and cache write-through saved the updates
    final_data = cfg.load_cache()
    # Initial views (10) + 10 threads * 30 iterations = 310 views
    expected_views = 10 + 10 * 30
    assert final_data[0]["views"] == expected_views, f"Expected {expected_views} views, got {final_data[0]['views']}"
    
    # Cleanup cache file
    if os.path.exists('movies_cache.json'):
        try:
            os.remove('movies_cache.json')
        except:
            pass
