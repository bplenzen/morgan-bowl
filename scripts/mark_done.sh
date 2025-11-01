#!/bin/bash
# Mark a task as complete

TASK_NUM=$1
PROGRESS_FILE="CODE_REVIEW_PROGRESS.md"

if [ -z "$TASK_NUM" ]; then
    echo "Usage: ./scripts/mark_done.sh <task_number>"
    exit 1
fi

# Replace first occurrence of "- [ ] **#$TASK_NUM" with "- [x] **#$TASK_NUM"
# macOS sed requires empty string for -i, Linux doesn't
if [[ "$OSTYPE" == "darwin"* ]]; then
    sed -i '' "0,/^- \[ \] \*\*#${TASK_NUM}/s//- [x] **#${TASK_NUM}/" "$PROGRESS_FILE"
else
    sed -i "0,/^- \[ \] \*\*#${TASK_NUM}/s//- [x] **#${TASK_NUM}/" "$PROGRESS_FILE"
fi

# Update last updated date
if [[ "$OSTYPE" == "darwin"* ]]; then
    sed -i '' "s/Last updated: .*/Last updated: $(date +%Y-%m-%d)/" "$PROGRESS_FILE"
else
    sed -i "s/Last updated: .*/Last updated: $(date +%Y-%m-%d)/" "$PROGRESS_FILE"
fi

echo "✅ Task #$TASK_NUM marked complete"
echo ""
echo "🔜 Next task:"
./scripts/next_task.sh
