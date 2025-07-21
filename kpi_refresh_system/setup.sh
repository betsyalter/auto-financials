#!/bin/bash

echo "Setting up KPI Refresh System..."

# Create directory structure
mkdir -p data/output data/csv logs config

# Copy example files
cp .env.example .env

echo "Please edit the following files:"
echo "1. .env - Add your Canalyst API token"
echo "2. config/company_mappings.csv - Add ticker to CSIN mappings"
echo "3. config/kpi_mappings.csv - Add KPI selections"

echo "Setup complete!"