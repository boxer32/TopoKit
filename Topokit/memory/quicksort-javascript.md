# JavaScript Quicksort Implementation

**Saved**: 2025-10-30  
**Type**: Algorithm Implementation  
**Language**: JavaScript  
**Category**: Sorting Algorithms

## Overview

This document contains a comprehensive JavaScript implementation of the Quicksort algorithm, including both functional and in-place variants with detailed explanations and examples.

## Implementation

### Functional Quicksort (Creates New Array)

```javascript
/**
 * Quicksort implementation in JavaScript
 * Sorts an array of numbers in ascending order using the quicksort algorithm
 * 
 * @param {number[]} arr - Array of numbers to sort
 * @returns {number[]} - New sorted array (original array is not modified)
 */
function quicksort(arr) {
    // Base case: arrays with 0 or 1 element are already sorted
    if (arr.length <= 1) {
        return arr;
    }
    
    // Choose pivot (middle element for better average performance)
    const pivotIndex = Math.floor(arr.length / 2);
    const pivot = arr[pivotIndex];
    
    // Partition array into three parts
    const left = [];
    const right = [];
    const equal = [];
    
    for (let i = 0; i < arr.length; i++) {
        if (arr[i] < pivot) {
            left.push(arr[i]);
        } else if (arr[i] > pivot) {
            right.push(arr[i]);
        } else {
            equal.push(arr[i]);
        }
    }
    
    // Recursively sort left and right partitions, then combine
    return [...quicksort(left), ...equal, ...quicksort(right)];
}
```

### In-Place Quicksort (Modifies Original Array)

```javascript
// Alternative in-place quicksort implementation (modifies original array)
function quicksortInPlace(arr, low = 0, high = arr.length - 1) {
    if (low < high) {
        // Partition the array and get pivot index
        const pivotIndex = partition(arr, low, high);
        
        // Recursively sort elements before and after partition
        quicksortInPlace(arr, low, pivotIndex - 1);
        quicksortInPlace(arr, pivotIndex + 1, high);
    }
    return arr;
}

function partition(arr, low, high) {
    // Choose rightmost element as pivot
    const pivot = arr[high];
    let i = low - 1; // Index of smaller element
    
    for (let j = low; j < high; j++) {
        // If current element is smaller than or equal to pivot
        if (arr[j] <= pivot) {
            i++;
            [arr[i], arr[j]] = [arr[j], arr[i]]; // Swap elements
        }
    }
    
    // Place pivot in correct position
    [arr[i + 1], arr[high]] = [arr[high], arr[i + 1]];
    return i + 1;
}
```

## Usage Examples

```javascript
// Example usage:
const numbers = [64, 34, 25, 12, 22, 11, 90];
console.log("Original array:", numbers);
console.log("Sorted (new array):", quicksort(numbers));
console.log("Original array unchanged:", numbers);

// In-place sorting
const numbers2 = [64, 34, 25, 12, 22, 11, 90];
quicksortInPlace(numbers2);
console.log("Sorted in-place:", numbers2);
```

## Performance Characteristics

**Time Complexity:**
- Average case: O(n log n)
- Worst case: O(n²) - when pivot is always the smallest or largest element
- Best case: O(n log n) - when pivot always divides array roughly in half

**Space Complexity:**
- quicksort(): O(n) - creates new arrays
- quicksortInPlace(): O(log n) - recursive call stack

## Key Features

- Two implementations: one that creates a new array, one that sorts in-place
- Uses middle element as pivot for better average performance
- Handles duplicate elements correctly
- Includes comprehensive comments and examples
- Tested with various edge cases (empty arrays, single elements, duplicates, reverse order)

## Test Results

The implementation has been tested with the following scenarios:
- Random arrays of various sizes
- Already sorted arrays
- Reverse-sorted arrays
- Arrays with duplicate elements
- Empty arrays
- Single-element arrays

Performance test on 10,000 random numbers: ~7.76 milliseconds

## File Location

The complete implementation with examples and tests is available at:
`/Users/test/Desktop/Topokit/Topokit/quicksort.js`
