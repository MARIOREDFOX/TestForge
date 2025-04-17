class HealthTests:
    def run(self, host_list):
        for host in host_list:
            self.run_cxl_health_check(host)

    def run_cxl_health_check(self, host):
        print(f"[CXLHealthCheck] Running on host: {host}")
        # Insert the actual SSH/command execution logic here

