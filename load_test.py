#!/usr/bin/env python3
"""
Load testing script for memes-ranker application.
Tests the application's ability to handle concurrent users.
"""

import asyncio
import aiohttp
import random
import time
from typing import Dict, Any


class LoadTester:
    def __init__(self, base_url: str = "http://localhost", concurrent_users: int = 100):
        self.base_url = base_url
        self.concurrent_users = concurrent_users
        self.results = []

    async def simulate_user_session(
        self, session: aiohttp.ClientSession, user_id: int
    ) -> Dict[str, Any]:
        """Simulate a single user session with the application."""
        user_results = {
            "user_id": user_id,
            "requests": [],
            "errors": 0,
            "total_time": 0,
        }

        start_time = time.time()

        try:
            # 1. Load main page (get session cookie)
            async with session.get(f"{self.base_url}/") as response:
                if response.status == 200:
                    user_results["requests"].append(
                        {
                            "endpoint": "/",
                            "status": 200,
                            "time": time.time() - start_time,
                        }
                    )
                else:
                    user_results["errors"] += 1

            # 2. Check session status
            async with session.get(f"{self.base_url}/api/session/status") as response:
                if response.status == 200:
                    user_results["requests"].append(
                        {
                            "endpoint": "/api/session/status",
                            "status": 200,
                            "time": time.time() - start_time,
                        }
                    )
                else:
                    user_results["errors"] += 1

            # 3. Get memes list
            async with session.get(f"{self.base_url}/api/memes") as response:
                if response.status == 200:
                    memes_data = await response.json()
                    user_results["requests"].append(
                        {
                            "endpoint": "/api/memes",
                            "status": 200,
                            "time": time.time() - start_time,
                        }
                    )

                    # 4. Submit random rankings for available memes
                    memes = memes_data.get("memes", [])
                    if memes:
                        for meme in memes[:3]:  # Rate first 3 memes
                            ranking_data = {
                                "meme_id": meme["id"],
                                "score": random.randint(1, 10),
                            }

                            async with session.post(
                                f"{self.base_url}/rank",
                                json=ranking_data,
                                headers={"Content-Type": "application/json"},
                            ) as rank_response:
                                if rank_response.status == 200:
                                    user_results["requests"].append(
                                        {
                                            "endpoint": "/rank",
                                            "status": 200,
                                            "time": time.time() - start_time,
                                        }
                                    )
                                else:
                                    user_results["errors"] += 1

                            # Small delay between rankings
                            await asyncio.sleep(0.1)
                else:
                    user_results["errors"] += 1

            # 5. Get statistics
            async with session.get(f"{self.base_url}/api/stats") as response:
                if response.status == 200:
                    user_results["requests"].append(
                        {
                            "endpoint": "/api/stats",
                            "status": 200,
                            "time": time.time() - start_time,
                        }
                    )
                else:
                    user_results["errors"] += 1

        except Exception as e:
            user_results["errors"] += 1
            user_results["exception"] = str(e)

        user_results["total_time"] = time.time() - start_time
        return user_results

    async def run_load_test(self) -> Dict[str, Any]:
        """Run the load test with concurrent users."""
        print(f"Starting load test with {self.concurrent_users} concurrent users...")
        print(f"Target URL: {self.base_url}")

        connector = aiohttp.TCPConnector(limit=self.concurrent_users * 2)
        timeout = aiohttp.ClientTimeout(total=30)

        async with aiohttp.ClientSession(
            connector=connector, timeout=timeout, cookie_jar=aiohttp.CookieJar()
        ) as session:
            # Create tasks for all users
            tasks = []
            for user_id in range(self.concurrent_users):
                task = asyncio.create_task(self.simulate_user_session(session, user_id))
                tasks.append(task)

            # Run all tasks concurrently
            test_start = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            test_duration = time.time() - test_start

            # Process results
            successful_users = 0
            total_requests = 0
            total_errors = 0
            response_times = []

            for result in results:
                if isinstance(result, Exception):
                    total_errors += 1
                    continue

                successful_users += 1
                total_requests += len(result["requests"])
                total_errors += result["errors"]
                response_times.extend([req["time"] for req in result["requests"]])

            # Calculate statistics
            avg_response_time = (
                sum(response_times) / len(response_times) if response_times else 0
            )
            max_response_time = max(response_times) if response_times else 0
            min_response_time = min(response_times) if response_times else 0

            requests_per_second = (
                total_requests / test_duration if test_duration > 0 else 0
            )

            test_results = {
                "concurrent_users": self.concurrent_users,
                "test_duration": test_duration,
                "successful_users": successful_users,
                "total_requests": total_requests,
                "total_errors": total_errors,
                "requests_per_second": requests_per_second,
                "avg_response_time": avg_response_time,
                "min_response_time": min_response_time,
                "max_response_time": max_response_time,
                "error_rate": (total_errors / total_requests * 100)
                if total_requests > 0
                else 0,
            }

            return test_results

    def print_results(self, results: Dict[str, Any]):
        """Print formatted test results."""
        print("\n" + "=" * 60)
        print("LOAD TEST RESULTS")
        print("=" * 60)
        print(f"Concurrent Users: {results['concurrent_users']}")
        print(f"Test Duration: {results['test_duration']:.2f} seconds")
        print(f"Successful Users: {results['successful_users']}")
        print(f"Total Requests: {results['total_requests']}")
        print(f"Total Errors: {results['total_errors']}")
        print(f"Requests/Second: {results['requests_per_second']:.2f}")
        print(f"Error Rate: {results['error_rate']:.2f}%")
        print(f"Avg Response Time: {results['avg_response_time']:.3f}s")
        print(f"Min Response Time: {results['min_response_time']:.3f}s")
        print(f"Max Response Time: {results['max_response_time']:.3f}s")
        print("=" * 60)

        # Performance assessment
        if results["error_rate"] < 1:
            print("✅ EXCELLENT: Error rate < 1%")
        elif results["error_rate"] < 5:
            print("⚠️  GOOD: Error rate < 5%")
        else:
            print("❌ POOR: Error rate >= 5%")

        if results["avg_response_time"] < 1:
            print("✅ EXCELLENT: Average response time < 1s")
        elif results["avg_response_time"] < 3:
            print("⚠️  GOOD: Average response time < 3s")
        else:
            print("❌ POOR: Average response time >= 3s")

        if results["requests_per_second"] > 100:
            print("✅ EXCELLENT: > 100 requests/second")
        elif results["requests_per_second"] > 50:
            print("⚠️  GOOD: > 50 requests/second")
        else:
            print("❌ POOR: < 50 requests/second")


async def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Load test the memes-ranker application"
    )
    parser.add_argument(
        "--url", default="http://localhost", help="Base URL of the application"
    )
    parser.add_argument(
        "--users", type=int, default=100, help="Number of concurrent users"
    )
    parser.add_argument(
        "--scale-test",
        action="store_true",
        help="Run scaling test (100, 500, 1000, 2000 users)",
    )

    args = parser.parse_args()

    if args.scale_test:
        print("Running scaling test...")
        user_counts = [100, 500, 1000, 2000]
        all_results = []

        for user_count in user_counts:
            print(f"\n--- Testing with {user_count} concurrent users ---")
            tester = LoadTester(args.url, user_count)
            results = await tester.run_load_test()
            tester.print_results(results)
            all_results.append(results)

            # Wait between tests
            await asyncio.sleep(5)

        # Summary
        print("\n" + "=" * 60)
        print("SCALING TEST SUMMARY")
        print("=" * 60)
        print(f"{'Users':<8} {'RPS':<12} {'Errors':<8} {'Avg Time':<12}")
        print("-" * 60)
        for result in all_results:
            print(
                f"{result['concurrent_users']:<8} {result['requests_per_second']:<12.1f} {result['error_rate']:<8.1f}% {result['avg_response_time']:<12.3f}s"
            )

    else:
        tester = LoadTester(args.url, args.users)
        results = await tester.run_load_test()
        tester.print_results(results)


if __name__ == "__main__":
    asyncio.run(main())
