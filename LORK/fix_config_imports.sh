grep -rl "from config import" lork | while read file; do
  sed -i '' 's/from config import/from lork.config import/g' "$file"
done
