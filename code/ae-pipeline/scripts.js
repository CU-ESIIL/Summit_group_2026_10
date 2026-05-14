var soilMoistureRaw = ee.FeatureCollection('users/alicelheiman/CONUS_SCAN_SMS_-2in_yearly_2017_2025');

Map.setOptions('SATELLITE');
Map.centerObject(demoArea, 7);

// ============================================================
// Shared configuration
// ============================================================
var years = [2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024];
// SMAP palette: blue (dry) → green → yellow → red (wet).
// Predicted % VWC and SMAP m³/m³ share the same visual ramp:
// 0 % == 0.0 m³/m³, 50 % == 0.5 m³/m³ — colors are directly comparable.
var predictedVis = { min: 0,   max: 50,  palette: ['0300ff', '418504', 'efff07', 'efff07', 'ff0303'] };
var smapVis      = { min: 0.0, max: 0.5, palette: ['0300ff', '418504', 'efff07', 'efff07', 'ff0303'] };

// Pre-filter once: drop rows with no target value
var soilMoisturePoints = soilMoistureRaw
  .filter(ee.Filter.notNull(['mean_soil_moisture']));

// ============================================================
// Per-year loop
// Queues 2 export tasks per year → 16 PNG files total in Drive
// Set mapYear to preview that year's layers on the interactive map
// ============================================================
var mapYear = 2022;

years.forEach(function(year) {
  var startDate = ee.Date.fromYMD(year, 1, 1);
  var endDate   = startDate.advance(1, 'year');

  // --- Satellite Embeddings (predictors) ---
  var emb = ee.ImageCollection('GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL')
    .filter(ee.Filter.date(startDate, endDate))
    .filter(ee.Filter.bounds(demoArea));

  var embImage = emb.mosaic()
    .setDefaultProjection(ee.Image(emb.first()).select(0).projection());

  // --- Training sample ---
  var training = embImage.sampleRegions({
    collection: soilMoisturePoints
      .filter(ee.Filter.eq('year', year))
      .filter(ee.Filter.bounds(demoArea)),
    properties: ['mean_soil_moisture'],
    scale: 10,
    tileScale: 16
  }).filter(ee.Filter.notNull(['mean_soil_moisture']));

  // --- Random Forest regression ---
  var model = ee.Classifier.smileRandomForest(50)
    .setOutputMode('REGRESSION')
    .train({
      features: training,
      classProperty: 'mean_soil_moisture',
      inputProperties: embImage.bandNames()
    });

  var predicted = embImage
    .classify({ classifier: model, outputName: 'mean_soil_moisture' })
    .clip(demoArea);

  // --- SMAP annual mean (note: 2024 coverage may be incomplete) ---
  var smap = ee.ImageCollection('NASA/SMAP/SPL3SMP_E/005')
    .filter(ee.Filter.date(startDate, endDate))
    .filter(ee.Filter.bounds(demoArea))
    .select('soil_moisture_am')
    .mean()
    .clip(demoArea);

  // --- Inline thumbnails in the console ---
  var thumbParams = { region: demoArea, dimensions: 512, crs: 'EPSG:4326' };

  print('=== Year ' + year + ' ===');
  print('  Training samples:', training.size());
  print('  Predicted ' + year + ':');
  print(ui.Thumbnail({ image: predicted.visualize(predictedVis), params: thumbParams }));
  print('  SMAP ' + year + ':');
  print(ui.Thumbnail({ image: smap.visualize(smapVis),      params: thumbParams }));

  // --- Interactive map preview for one year only ---
  if (year === mapYear) {
    Map.addLayer(predicted, predictedVis, 'Predicted ' + year);
    Map.addLayer(smap, smapVis, 'SMAP ' + year);
    Map.addLayer(
      soilMoisturePoints
        .filter(ee.Filter.eq('year', year))
        .filter(ee.Filter.bounds(demoArea)),
      { color: 'ff0000' }, 'Training Points ' + year
    );
  }
});
