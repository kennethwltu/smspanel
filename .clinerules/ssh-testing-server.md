---
name: ssh-testing-server
description: Use this agent when you need to test or deploy the smspanel application on the testing CentOS 7 server. This agent specializes in SSH operations, server testing, and deployment verification on the designated testing server.
author: Kenneth
version: 1.0
tags: ["ssh", "testing", "deployment", "centos", "server", "smspanel"]
---

# SSH Testing Server Guide for AI

## Overview

This rule provides guidance for AI agents on when and how to use SSH to connect to the testing server for the smspanel application. The testing server is a CentOS 7 system that can be accessed via SSH for deployment testing, debugging, and verification purposes.

## Server Information

- **Server Address**: `10.34.60.243`
- **Username**: `admin`
- **SSH Command**: `ssh admin@10.34.60.243`
- **Operating System**: CentOS 7
- **Purpose**: Testing and deployment of smspanel application

## When to Use SSH to the Testing Server

Use SSH to connect to the testing server when you need to:

1. **Deployment Testing**: Test Docker Compose deployment of smspanel
2. **Service Verification**: Check if smspanel services are running
3. **Log Inspection**: Examine application logs on the server
4. **Configuration Testing**: Test environment variables and configurations
5. **Network Testing**: Verify connectivity between services
6. **Database Operations**: Check database status and integrity
7. **Performance Testing**: Monitor resource usage on the server
8. **Security Testing**: Verify firewall and security configurations

## Common SSH Commands for Testing

### Basic Connection
```bash
# Connect to the testing server
ssh admin@10.34.60.243
```

### Execute Single Commands Remotely
```bash
# Run a single command without interactive session
ssh admin@10.34.60.243 "command_to_run"

# Examples:
ssh admin@10.34.60.243 "docker ps"
ssh admin@10.34.60.243 "systemctl status docker"
ssh admin@10.34.60.243 "ls -la /opt/smspanel/"
```

### Common Testing Operations

#### 1. Check Docker Status
```bash
ssh admin@10.34.60.243 "docker ps"
ssh admin@10.34.60.243 "docker-compose ps"
ssh admin@10.60.34.243 "docker logs smspanel_smspanel_1"
```

#### 2. Check Application Status
```bash
# Check if application is accessible
ssh admin@10.34.60.243 "curl -f http://localhost:3570/health || echo 'Application not responding'"

# Check specific endpoints
ssh admin@10.34.60.243 "curl -f http://localhost:3570/api/sms"
```

#### 3. View Logs
```bash
# View Docker container logs
ssh admin@10.34.60.243 "docker logs --tail 50 smspanel_smspanel_1"

# View system logs
ssh admin@10.34.60.243 "journalctl -u docker --since '1 hour ago'"
```

#### 4. Database Operations
```bash
# Check database file
ssh admin@10.34.60.243 "ls -lh /opt/smspanel/instance/sms.db"

# Backup database
ssh admin@10.34.60.243 "cp /opt/smspanel/instance/sms.db /opt/smspanel/instance/sms.db.backup.$(date +%Y%m%d)"
```

#### 5. Resource Monitoring
```bash
# Check system resources
ssh admin@10.34.60.243 "free -h"
ssh admin@10.34.60.243 "df -h"
ssh admin@10.34.60.243 "top -bn1 | head -20"
```

## Testing Workflows

### 1. Full Deployment Test
```bash
# Connect to server
ssh admin@10.34.60.243

# Navigate to application directory
cd /opt/smspanel

# Stop existing services
docker-compose down

# Pull latest changes (if using git)
git pull

# Start services
docker-compose up -d

# Verify services are running
docker-compose ps

# Check application health
curl -f http://localhost:3570/ || echo "Application failed to start"
```

### 2. Quick Health Check
```bash
# One-liner health check
ssh admin@10.34.60.243 "cd /opt/smspanel && docker-compose ps && echo '---' && curl -s -o /dev/null -w '%{http_code}' http://localhost:3570/"
```

### 3. Log Analysis
```bash
# Get recent error logs
ssh admin@10.34.60.243 "docker logs smspanel_smspanel_1 --tail 100 | grep -i error"

# Get application startup logs
ssh admin@10.34.60.243 "docker logs smspanel_smspanel_1 --since '10m ago'"
```

## Security Considerations

1. **SSH Key Authentication**: The SSH connection uses key-based authentication (already configured)
2. **Firewall Rules**: Ensure port 3570 is open if testing from external network
3. **Proxy Configuration**: The application may require proxy settings as shown in docker-compose.yml
4. **Sensitive Data**: Never log or expose credentials in command output

## Troubleshooting

### Common Issues and Solutions

1. **SSH Connection Failed**
   ```bash
   # Check network connectivity
   ping 10.34.60.243
   
   # Check SSH service
   ssh -v admin@10.34.60.243
   ```

2. **Docker Not Running**
   ```bash
   ssh admin@10.34.60.243 "sudo systemctl start docker"
   ssh admin@10.34.60.243 "sudo systemctl enable docker"
   ```

3. **Application Not Accessible**
   ```bash
   # Check if container is running
   ssh admin@10.34.60.243 "docker ps | grep smspanel"
   
   # Check port binding
   ssh admin@10.34.60.243 "netstat -tlnp | grep 3570"
   
   # Check firewall
   ssh admin@10.34.60.243 "sudo firewall-cmd --list-ports | grep 3570"
   ```

## Best Practices

1. **Always verify** commands before executing them on the server
2. **Use descriptive comments** when providing SSH command examples
3. **Test connectivity** before running complex deployment commands
4. **Monitor resource usage** during testing to avoid server overload
5. **Clean up** test resources when finished
6. **Document** any issues found during testing

## Integration with smspanel Project

When testing the smspanel application on the server, consider:

1. **Environment Variables**: Match those in docker-compose.yml
2. **Database Location**: Typically at `/opt/smspanel/instance/sms.db`
3. **Port Configuration**: Application runs on port 3570
4. **Network Configuration**: May require proxy settings for external SMS gateway

## Example Testing Scenario

**Scenario**: Test new Docker image deployment

```bash
# 1. Connect to server and check current status
ssh admin@10.34.60.243 "cd /opt/smspanel && docker-compose ps"

# 2. Pull latest Docker images
ssh admin@10.34.60.243 "cd /opt/smspanel && docker-compose pull"

# 3. Restart services
ssh admin@10.34.60.243 "cd /opt/smspanel && docker-compose down && docker-compose up -d"

# 4. Verify deployment
ssh admin@10.34.60.243 "sleep 10 && cd /opt/smspanel && docker-compose ps && curl -f http://localhost:3570/"

# 5. Check logs for errors
ssh admin@10.34.60.243 "docker logs smspanel_smspanel_1 --tail 50 | grep -i error || echo 'No errors found'"
```

This rule ensures AI agents can effectively use SSH to test and deploy the smspanel application on the designated testing server.
