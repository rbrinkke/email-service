#!/bin/bash
# Fix relative imports to absolute imports

echo "Fixing relative imports..."

# Fix providers
sed -i 's/from \.\.models/from models/g' providers/*.py
sed -i 's/from \.\.config/from config/g' providers/*.py

# Fix services
sed -i 's/from \.\.models/from models/g' services/*.py
sed -i 's/from \.\.config/from config/g' services/*.py
sed -i 's/from \.\.redis/from redis/g' services/*.py
sed -i 's/from \.\.providers/from providers/g' services/*.py
sed -i 's/from \.\.workers/from workers/g' services/*.py

# Fix workers
sed -i 's/from \.\.models/from models/g' workers/*.py
sed -i 's/from \.\.config/from config/g' workers/*.py
sed -i 's/from \.\.providers/from providers/g' workers/*.py
sed -i 's/from \.\.services/from services/g' workers/*.py

echo "Done!"