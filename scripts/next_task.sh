#!/bin/bash
# Automatically shows the next uncompleted task prompt

PROGRESS_FILE="CODE_REVIEW_PROGRESS.md"
PROMPTS_DIR="prompts"

# Find first unchecked task
NEXT_TASK=$(grep -n "^- \[ \]" "$PROGRESS_FILE" | head -1 | sed 's/.*#\([0-9]*\).*/\1/')

if [ -z "$NEXT_TASK" ]; then
    echo "🎉 All tasks complete!"
    exit 0
fi

# Find corresponding prompt file (handle leading zeros)
PROMPT_FILE=$(ls "$PROMPTS_DIR" | grep "^0*${NEXT_TASK}_" | head -1)

if [ -z "$PROMPT_FILE" ]; then
    echo "❌ No prompt file found for task #$NEXT_TASK"
    exit 1
fi

echo "📋 Next task: #$NEXT_TASK"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
cat "$PROMPTS_DIR/$PROMPT_FILE"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ After completing, run: ./scripts/mark_done.sh $NEXT_TASK"
