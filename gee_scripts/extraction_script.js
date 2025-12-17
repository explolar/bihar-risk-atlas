var blocks = ee.FeatureCollection("projects/xward-481405/assets/blocks_bihar");

Map.centerObject(blocks, 7);
Map.addLayer(blocks, {color: 'red'}, "Bihar Blocks");
var blocks = ee.FeatureCollection("projects/xward-481405/assets/blocks_bihar");

var startDate = '2019-01-01';
var endDate   = '2024-12-31';

// Sentinel-2 NDVI (image-level, safe)
var s2 = ee.ImageCollection("COPERNICUS/S2_SR")
  .filterBounds(blocks)
  .filterDate(startDate, endDate)
  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 40))
  .map(function(img) {
    var ndvi = img
      .normalizedDifference(['B8', 'B4'])
      .rename('NDVI');

    return ndvi.copyProperties(img, ['system:time_start']);
  });

// 🔒 REDUCE PER IMAGE (KEY FIX — SAME AS ET)
var ndviTable = s2.map(function(img) {
  var date = ee.Date(img.get('system:time_start'));

  return img.reduceRegions({
    collection: blocks,
    reducer: ee.Reducer.mean(),
    scale: 10
  }).map(function(f) {
    return f.set({
      'year': date.get('year'),
      'month': date.get('month')
    });
  });
}).flatten();

// Export NDVI
Export.table.toDrive({
  collection: ndviTable,
  description: 'Bihar_Block_NDVI',
  fileFormat: 'CSV'
});


var chirps = ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY")
  .filterBounds(blocks)
  .filterDate(startDate, endDate);

// Monthly Rainfall
var monthlyRain = ee.ImageCollection(
  ee.List.sequence(2019, 2024).map(function(y) {
    return ee.List.sequence(1,12).map(function(m) {
      var start = ee.Date.fromYMD(y, m, 1);
      var end   = start.advance(1, 'month');
      var rain = chirps.filterDate(start, end).sum().rename('Rainfall');
      return rain.set({
        'year': y,
        'month': m,
        'system:time_start': start.millis()
      });
    });
  }).flatten()
);

// Reduce rainfall to blocks
var rainTable = monthlyRain.map(function(img) {
  return img.reduceRegions({
    collection: blocks,
    reducer: ee.Reducer.mean(),
    scale: 5000
  }).map(function(f) {
    return f.set({
      'year': img.get('year'),
      'month': img.get('month')
    });
  });
}).flatten();

// Export Rainfall
Export.table.toDrive({
  collection: rainTable,
  description: 'Bihar_Block_Rainfall',
  fileFormat: 'CSV'
});

var blocks = ee.FeatureCollection("projects/xward-481405/assets/blocks_bihar");

var startDate = '2019-01-01';
var endDate   = '2024-12-31';

// MODIS ET (8-day, scaled)
var etCol = ee.ImageCollection("MODIS/061/MOD16A2")
  .filterBounds(blocks)
  .filterDate(startDate, endDate)
  .select('ET')
  .map(function(img) {
    return img
      .multiply(0.1) // scale factor
      .rename('ET')
      .copyProperties(img, ['system:time_start']);
  });

// 🔒 REDUCE FIRST, AGGREGATE LATER (KEY DIFFERENCE)
var etTable = etCol.map(function(img) {
  var date = ee.Date(img.get('system:time_start'));

  return img.reduceRegions({
    collection: blocks,
    reducer: ee.Reducer.mean(),
    scale: 500
  }).map(function(f) {
    return f.set({
      'year': date.get('year'),
      'month': date.get('month')
    });
  });
}).flatten();

// Export ET table
Export.table.toDrive({
  collection: etTable,
  description: 'Bihar_Block_ET',
  fileFormat: 'CSV'
});

var blocks = ee.FeatureCollection("projects/xward-481405/assets/blocks_bihar");

var ndvi = ee.ImageCollection("MODIS/061/MOD13Q1")
  .filterBounds(blocks)
  .filterDate('2019-01-01', '2024-12-31')
  .select('NDVI')
  .map(function(img) {
    return img.multiply(0.0001)
      .rename('NDVI')
      .copyProperties(img, ['system:time_start']);
  });

var ndviTable = ndvi.map(function(img) {
  var date = ee.Date(img.get('system:time_start'));
  return img.reduceRegions({
    collection: blocks,
    reducer: ee.Reducer.mean(),
    scale: 250
  }).map(function(f) {
    return f.set({
      'year': date.get('year'),
      'month': date.get('month')
    });
  });
}).flatten();

Export.table.toDrive({
  collection: ndviTable,
  description: 'Bihar_Block_NDVI',
  fileFormat: 'CSV'
});
var blocks = ee.FeatureCollection("projects/xward-481405/assets/blocks_bihar");

print("Block properties:", blocks.first());