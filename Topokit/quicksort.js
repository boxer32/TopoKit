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

// Example usage and testing
function runExamples() {
    console.log("=== Quicksort Examples ===\n");
    
    const numbers = [64, 34, 25, 12, 22, 11, 90];
    console.log("Original array:", numbers);
    console.log("Sorted (new array):", quicksort(numbers));
    console.log("Original array unchanged:", numbers);
    console.log();
    
    // In-place sorting
    const numbers2 = [64, 34, 25, 12, 22, 11, 90];
    console.log("Before in-place sort:", numbers2);
    quicksortInPlace(numbers2);
    console.log("After in-place sort:", numbers2);
    console.log();
    
    // Test with different arrays
    const testCases = [
        [5, 2, 8, 1, 9],
        [1],
        [],
        [3, 3, 3, 3],
        [9, 8, 7, 6, 5, 4, 3, 2, 1],
        [1, 2, 3, 4, 5]
    ];
    
    testCases.forEach((testCase, index) => {
        console.log(`Test case ${index + 1}:`, testCase);
        console.log("Sorted:", quicksort(testCase));
        console.log();
    });
}

// Performance testing
function performanceTest() {
    console.log("=== Performance Test ===");
    
    // Generate random array
    const size = 10000;
    const randomArray = Array.from({ length: size }, () => Math.floor(Math.random() * 1000));
    
    console.log(`Sorting array of ${size} random numbers...`);
    
    const startTime = performance.now();
    const sorted = quicksort(randomArray);
    const endTime = performance.now();
    
    console.log(`Time taken: ${(endTime - startTime).toFixed(2)} milliseconds`);
    console.log(`First 10 elements: ${sorted.slice(0, 10).join(', ')}`);
    console.log(`Last 10 elements: ${sorted.slice(-10).join(', ')}`);
}

// Export functions for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { quicksort, quicksortInPlace, partition };
}

// Run examples if this file is executed directly
if (typeof require !== 'undefined' && require.main === module) {
    runExamples();
    performanceTest();
}
